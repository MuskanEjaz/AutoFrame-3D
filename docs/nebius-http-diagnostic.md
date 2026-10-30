# Nebius HTTP 400 diagnostic

Update 2026-10-28: subsequent operator-confirmed testing found control characters
in an earlier key and HTTP 422 resolved by the named name/schema envelope.
The existing envelope edits are now preserved for release. A successful dev-01
run used 88a3e73 plus that uncommitted patch, not the later release commit.
See [current submission brief](submission-ready.md) and
[reviewed evidence](../audit_evidence/live_integration_20261028/verification.json).
The offline findings below describe the earlier diagnostic checkpoint, not
current compatibility. The probe now uses the named envelope.

The preserved diagnostic-dev01-a38c339b72c0426f985944edd50b1eb7 capture
confirms first-request HTTP 400, no tools, and no retained provider code.
The rejected field and root cause remain unknown. Neither failed capture
establishes successful inference or model-quality failure.

Offline comparison on 2026-10-28:

- The investigation sends model nvidia/Nemotron-3_5-Lightning, temperature 0,
  max_tokens 1200, response_format with type json_schema and the direct
  Action.model_json_schema(), and system/user messages. No reasoning options
  or max_completion_tokens are sent.
- Action uses $defs/$ref, enums, required fields, additionalProperties false
  for models, string-valued additionalProperties for tool arguments, and
  string/array length bounds. Local schema, action, tool and citation checks
  remain unchanged.
- The official structured-output guide shows a direct Pydantic schema in its
  Python example, but also a name/schema/strict envelope. Its schema example
  uses constraints and nested objects; it gives no model-specific guarantee
  for all Action constructs. The API reference contradicts the guide by
  describing only json_object/text response formats. This is insufficient
  evidence to change the request envelope or remove schema constraints.
- The API reference permits temperature 0 and positive max_tokens; it also
  documents max_completion_tokens including reasoning, and reasoning_effort
  options none/minimal/low/medium/high/xhigh. The official Nemotron page
  confirms the exact model ID and reasoning/tool use, but does not establish
  a mandatory reasoning setting or this schema's compatibility. No token or
  reasoning change is demonstrably required.

Sources:
- https://docs.tokenfactory.nebius.com/ai-models-inference/json
- https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion
- https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference

Confirmed diagnostic defect fixed: the HTTP handler discarded structured
validation details. It now reads at most 4097 bytes, parses only bodies up
to 4096 bytes, and emits at most four sanitized entries. Locations use known
field names, types/codes use an allowlist, reasons are fixed labels, and
unknown prose/input/ctx are omitted. It never emits raw bodies or messages.

Manual next step, from the worktree with NEBIUS_API_KEY already configured:

```powershell
.venv\Scripts\python.exe scripts/diagnose_nebius.py --live
```

This makes exactly one request, no retries or tool execution, with the same
schema/model/temperature, a constant prompt and max_tokens 128. Python
pathlib creates a fresh artifacts/nebius-http-probe-<uuid> directory. Only
sanitized diagnostics are printed/saved. A successful probe does not prove
the original larger request would succeed; a length finish is not another
HTTP rejection. No probe was run during implementation.
