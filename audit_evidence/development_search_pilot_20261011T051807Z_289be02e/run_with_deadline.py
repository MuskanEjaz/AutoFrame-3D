"""Enforce a wall-clock ceiling on this one predeclared pilot process tree."""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
command = [sys.executable, "-B", str(ROOT / "scripts/development_search_pilot.py"), "--run", str(OUT)]
guard = {
    "command": ".\\.venv\\Scripts\\python.exe -B " + Path(__file__).relative_to(ROOT).as_posix(),
    "child_command": ".\\.venv\\Scripts\\python.exe -B scripts/development_search_pilot.py --run " + OUT.relative_to(ROOT).as_posix(),
    "guard_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "process_tree_wall_timeout_seconds": 895,
    "overall_limit_seconds": 900,
    "timeout_action": "Terminate only the freshly spawned pilot PID and descendants; no retry.",
}
(OUT / "execution_guard.json").write_text(json.dumps(guard, indent=2), encoding="utf-8")
started = time.monotonic()
child = subprocess.Popen(command, cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
try:
    result = child.wait(timeout=895)
except subprocess.TimeoutExpired:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True, timeout=4)
    else:
        child.kill()
    result = 124
guard["returncode"] = result
guard["elapsed_seconds"] = time.monotonic() - started
(OUT / "execution_guard.json").write_text(json.dumps(guard, indent=2), encoding="utf-8")
sys.exit(result)
