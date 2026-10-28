"""One explicit manual schema probe; no investigation, tools, retries or dotenv."""
import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autoframe3d import investigation, nebius


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    if not args.live:
        parser.error("Explicit --live required for one provider request")
    if not nebius.configured():
        parser.error("NEBIUS_API_KEY must already be configured; no dotenv is loaded")
    directory = Path("artifacts") / ("nebius-http-probe-" + uuid4().hex)
    directory.mkdir(parents=True, exist_ok=False)
    # Keep suspect schema and request fields, replace evidence/user prompts with
    # one constant instruction and reduce output to 128 tokens. Never run tools.
    payload = {"model": nebius.DEFAULT_MODEL, "temperature": 0.0, "max_tokens": 128,
               "response_format": {"type": "json_schema", "json_schema": investigation.Action.model_json_schema()},
               "messages": [{"role": "user", "content":
                   'Return JSON: {"kind":"tools","calls":[],"findings":[]}'}]}
    try:
        nebius.chat_completion(payload, timeout=20.0, max_response_bytes=32768)
        result = {"stage": "response_received"}
    except nebius.ProviderError as error:
        result = error.diagnostic
    except TimeoutError:
        result = {"stage": "timeout"}
    except Exception:
        result = {"stage": "local_or_transport_error"}
    # Never persist the payload, response content, or exception text.
    with (directory / "diagnostic.json").open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"output": str(directory / "diagnostic.json"), "diagnostic": result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
