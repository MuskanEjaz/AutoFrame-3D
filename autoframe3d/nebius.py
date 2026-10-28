"""Shared Token Factory transport; no retries, bounded body and caller wait."""
import json
import os
import queue
import threading
import urllib.error
import urllib.request

NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
DEFAULT_MODEL = "nvidia/Nemotron-3_5-Lightning"


class ProviderError(RuntimeError):
    def __init__(self, stage, **details):
        super().__init__("Nebius provider failed or returned an invalid/incomplete response")
        self.diagnostic = {"stage": stage, **details}


def validate_response(body):
    try:
        choice = body["choices"][0]
        content = choice["message"]["content"]
        finish = choice["finish_reason"]
    except (KeyError, TypeError, IndexError):
        raise ProviderError("response_shape") from None
    if finish != "stop":
        raise ProviderError("finish_reason", finish_reason=finish if isinstance(finish, str) and finish in (
            "length", "tool_calls", "content_filter", "function_call") else "other")
    if not isinstance(content, str):
        raise ProviderError("response_shape")
    if not content.strip():
        raise ProviderError("empty_content")
    return content


def configured():
    # Inspect availability only; never return the credential.
    return bool(os.environ.get("NEBIUS_API_KEY", "").strip())


def model_name():
    model = os.environ.get("NEBIUS_MODEL", DEFAULT_MODEL)
    if not model.startswith("nvidia/") or "nemotron" not in model.lower() or len(model) > 120:
        raise RuntimeError("Configure an NVIDIA Nemotron model identifier")
    return model


def chat_completion(payload, *, timeout=20.0, max_response_bytes=65536):
    key = os.environ.get("NEBIUS_API_KEY")
    if not configured():
        raise RuntimeError("NEBIUS_API_KEY is not configured")
    # Fixed official endpoint prevents model output/config from redirecting credentials.
    request = urllib.request.Request(
        NEBIUS_BASE_URL + "chat/completions", data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST",
    )
    result = queue.Queue(maxsize=1)

    def send():
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read(max_response_bytes + 1)
            if len(raw) > max_response_bytes:
                raise ProviderError("response_size")
            try:
                body = json.loads(raw)
            except (ValueError, UnicodeError):
                raise ProviderError("response_json") from None
            validate_response(body)
            result.put((body, None))
        except urllib.error.HTTPError as error:
            code = None
            try:
                with error:
                    raw = error.read(4097)
                parsed = json.loads(raw) if len(raw) <= 4096 else {}
                candidate = parsed.get("error", {}).get("code")
                if isinstance(candidate, str) and candidate in {
                    "invalid_request_error", "authentication_error", "permission_denied",
                    "rate_limit_exceeded", "model_not_found", "insufficient_quota", "server_error"}:
                    code = candidate
            except Exception:
                pass
            result.put((None, ProviderError("http_rejection", http_status=error.code, provider_code=code)))
        except Exception as error:
            # Do not expose provider bodies, request objects, or credentials.
            timed_out = isinstance(error, TimeoutError) or (
                isinstance(error, urllib.error.URLError) and isinstance(error.reason, TimeoutError))
            result.put((None, "timeout" if timed_out else error if isinstance(error, ProviderError)
                        else ProviderError("network" if isinstance(error, OSError) else "provider")))

    threading.Thread(target=send, daemon=True).start()
    try:
        body, error = result.get(timeout=timeout)
    except queue.Empty:
        raise TimeoutError("Nebius request deadline exceeded") from None
    if error == "timeout":
        raise TimeoutError("Nebius request deadline exceeded")
    if error:
        raise error from None
    return body
