"""Token-free watchdog (GitHub Actions cron): wake grokbot when jobs wait but no live runner.

Pings $GROKBOT_WEBHOOK_URL with {"event": "job_queued" | "runner_stale", ...} when
  - queue/ or running/ has jobs, and
  - the runner heartbeat (status branch) is missing, `stopped`, or older than STALE_MIN.
Silent otherwise. Never touches the queue.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import urllib.request
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
STALE_MIN = 20


def main() -> None:
    queued = [p.name for p in (LAB / "queue").glob("*.json")]
    running = [p.name for p in (LAB / "running").glob("*.json")]
    if not queued and not running:
        print("no pending jobs")
        return
    subprocess.run(["git", "-C", str(LAB), "fetch", "-q", "origin", "status"], check=False)
    raw = subprocess.run(["git", "-C", str(LAB), "show", "origin/status:heartbeat.json"],
                         capture_output=True, text=True).stdout
    hb = json.loads(raw) if raw else {}
    age_min = None
    if hb.get("at"):
        age_min = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(hb["at"])).total_seconds() / 60
    alive = hb.get("state") in ("running", "idle") and age_min is not None and age_min < STALE_MIN
    print(f"queued={len(queued)} running={len(running)} heartbeat={hb.get('state')} age_min={age_min}")
    if alive:
        return
    hook = os.environ.get("GROKBOT_WEBHOOK_URL")
    if not hook:
        print("::warning::runner down with pending jobs, but GROKBOT_WEBHOOK_URL is not set")
        return
    gpu = "T4"
    for p in (LAB / "queue").glob("*.json"):
        if json.loads(p.read_text(encoding="utf-8"))["spec"].get("gpu") == "L4":
            gpu = "L4"
    body = {"event": "runner_stale" if running else "job_queued", "pending": len(queued) + len(running),
            "gpu": gpu, "heartbeat": hb}
    req = urllib.request.Request(hook, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30)
    print(f"pinged grokbot: {body['event']}")


if __name__ == "__main__":
    main()
