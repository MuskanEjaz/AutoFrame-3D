"""Shared Token Factory transport; no retries, bounded body and caller wait."""
import json
import os
import queue
import threading
import urllib.error
import urllib.request

NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
DEFAULT_MODEL = "nvidia/Nemotron-3_5-Lightning"


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
                raise ValueError("response limit")
            body = json.loads(raw)
            choice = body["choices"][0]
            if choice.get("finish_reason") != "stop" or not isinstance(choice["message"]["content"], str):
                raise ValueError("incomplete completion")
            result.put((body, None))
        except Exception as error:
            # Do not expose provider bodies, request objects, or credentials.
            timed_out = isinstance(error, TimeoutError) or (
                isinstance(error, urllib.error.URLError) and isinstance(error.reason, TimeoutError))
            result.put((None, "timeout" if timed_out else "provider_or_response_error"))

    threading.Thread(target=send, daemon=True).start()
    try:
        body, error = result.get(timeout=timeout)
    except queue.Empty:
        raise TimeoutError("Nebius request deadline exceeded") from None
    if error == "timeout":
        raise TimeoutError("Nebius request deadline exceeded")
    if error:
        raise RuntimeError("Nebius provider failed or returned an invalid/incomplete response")
    return body
