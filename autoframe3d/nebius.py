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


# Provider strings are untrusted, including locations and validation messages.
# Emit only known vocabulary and fixed reason labels, never echoed values.
ERROR_CODES = frozenset({
    "invalid_request_error", "authentication_error", "permission_denied",
    "rate_limit_exceeded", "model_not_found", "insufficient_quota", "server_error",
    "validation_error", "invalid_parameter", "unsupported_parameter", "invalid_value",
    "missing", "value_error", "type_error", "extra_forbidden", "string_type",
    "dict_type", "list_type", "literal_error", "int_type", "greater_than_equal",
    "less_than_equal", "json_invalid", "model_attributes_type"})
ERROR_FIELDS = frozenset({
    "body", "query", "response_format", "json_schema", "schema", "name", "strict",
    "type", "properties", "additionalProperties", "$defs", "$ref", "required",
    "items", "enum", "title", "minLength", "maxLength", "minItems", "maxItems",
    "Action", "ToolCall", "Finding", "kind", "calls", "findings", "arguments",
    "text", "evidence_ids", "model", "messages", "role", "content", "temperature",
    "max_tokens", "max_completion_tokens", "reasoning_effort", "extra_body",
    "chat_template_kwargs", "enable_thinking", "reasoning_budget"})


def http_error_details(parsed):
    import re

    def allowed(value, vocabulary):
        key = os.environ.get("NEBIUS_API_KEY", "")
        return isinstance(value, str) and value in vocabulary and not (key and key in value)

    if not isinstance(parsed, dict):
        return []
    entries = []
    if isinstance(parsed.get("error"), dict):
        entries.append(parsed["error"])
    if isinstance(parsed.get("detail"), list):
        entries.extend(parsed["detail"][:4])
    output = []
    for entry in entries[:4]:
        if not isinstance(entry, dict):
            continue
        clean = {}
        for field in ("type", "code"):
            value = entry.get(field)
            if allowed(value, ERROR_CODES):
                clean[field] = value
        location = entry.get("loc", entry.get("param"))
        if isinstance(location, str) and len(location) <= 200:
            location = re.split(r"[./\[\]]+", location)
            location = [part for part in location if part]
        if isinstance(location, (list, tuple)) and 0 < len(location) <= 16:
            if all(allowed(part, ERROR_FIELDS) or type(part) is int and 0 <= part <= 10000
                   for part in location):
                clean["location"] = list(location)
        message = entry.get("msg", entry.get("message"))
        # Recognize only fixed validation prefixes; never copy message suffixes,
        # ctx/input fields, enum alternatives, values, or provider prose.
        if isinstance(message, str) and len(message) <= 1000:
            for prefix, reason in (
                ("field required", "required field missing"),
                ("extra inputs are not permitted", "extra field forbidden"),
                ("input should be a valid", "invalid value type or format"),
                ("input should be", "value violates constraint"),
                ("unsupported parameter", "unsupported parameter"),
                ("unknown parameter", "unknown parameter"),
                ("invalid schema", "invalid schema"),
                ("invalid json schema", "invalid schema"),
                ("value error,", "value validation failed"),
            ):
                if message.lower().startswith(prefix):
                    clean["reason"] = reason
                    break
        if clean:
            output.append(clean)
    return output


def validate_response(body):
    try:
        choice = body["choices"][0]
        content = choice["message"]["content"]
        finish = choice["finish_reason"]
    except (KeyError, TypeError, IndexError):
        raise ProviderError("response_shape") from None
    if finish != "stop":
        fields = {"finish_reason": finish if isinstance(finish, str) and finish in (
            "length", "tool_calls", "content_filter", "function_call") else "other"}
        # Retain only bounded token counters on rejected completions. Never
        # expose partial content, reasoning, request data, or other usage fields.
        usage = body.get("usage")
        if isinstance(usage, dict):
            safe_usage = {k: usage[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")
                          if k in usage and type(usage[k]) is int and 0 <= usage[k] <= 2**63 - 1}
            if safe_usage:
                fields["usage"] = safe_usage
        raise ProviderError("finish_reason", **fields)
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
    if not key:
        raise RuntimeError("NEBIUS_API_KEY is not configured")
    # Reject whitespace, controls (including CR/LF/DEL), and non-ASCII header
    # values unchanged. Never trim/repair or include the credential in errors.
    if any(ord(char) < 33 or ord(char) > 126 for char in key):
        raise ProviderError("invalid_credentials")
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
            details = []
            try:
                with error:
                    raw = error.read(4097)
                if len(raw) <= 4096:
                    details = http_error_details(json.loads(raw))
            except Exception:
                pass
            code = next((item["code"] for item in details if "code" in item), None)
            fields = {"http_status": error.code, "provider_code": code}
            if details:
                fields["validation_details"] = details
            result.put((None, ProviderError("http_rejection", **fields)))
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
