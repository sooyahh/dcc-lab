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


WORKERS = ["colab-a", "colab-b"]
NOTEBOOKS = {"colab-a": "lab_worker.ipynb", "colab-b": "lab_worker_2.ipynb"}


def read_heartbeats() -> dict[str, dict]:
    """Live view per worker name from the status branch (heartbeat_<worker>.json, plus legacy heartbeat.json)."""
    subprocess.run(["git", "-C", str(LAB), "fetch", "-q", "origin", "status"], check=False)
    names = subprocess.run(["git", "-C", str(LAB), "ls-tree", "--name-only", "origin/status"],
                           capture_output=True, text=True).stdout.split()
    hbs: dict[str, dict] = {}
    for n in names:
        if not n.startswith("heartbeat"):
            continue
        raw = subprocess.run(["git", "-C", str(LAB), "show", f"origin/status:{n}"],
                             capture_output=True, text=True).stdout
        hb = json.loads(raw) if raw else {}
        w = hb.get("worker")
        if w and (w not in hbs or hb.get("at", "") > hbs[w].get("at", "")):
            hbs[w] = hb
    return hbs


def is_live(hb: dict | None) -> bool:
    if not hb or not hb.get("at") or hb.get("state") not in ("running", "idle"):
        return False
    return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(hb["at"])).total_seconds() / 60 < STALE_MIN


def main() -> None:
    queued = [p.name for p in (LAB / "queue").glob("*.json")]
    running = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in (LAB / "running").glob("*.json")}
    if not queued and not running:
        print("no pending jobs")
        return
    max_workers = int(json.loads((LAB / "config.json").read_text(encoding="utf-8")).get("max_workers", 1))
    hbs = read_heartbeats()
    live = {w for w, hb in hbs.items() if is_live(hb)}
    # 1) a running job whose worker is down must be resumed by that worker's notebook (legacy names -> colab-a)
    need: list[str] = []
    for job in running.values():
        w = job.get("worker")
        w = w if w in WORKERS else WORKERS[0]
        if w not in live and w not in need:
            need.append(w)
    # 2) queued jobs beyond what idle live workers can take -> start more workers, up to max_workers
    busy = {job.get("worker") for job in running.values()}
    idle_live = [w for w in live if w not in busy]
    extra = len(queued) - len(idle_live)
    for w in WORKERS[:max_workers]:
        if extra <= 0:
            break
        if w not in live and w not in need and w not in busy:
            need.append(w)
            extra -= 1
    print(f"queued={len(queued)} running={len(running)} live={sorted(live)} need={need}")
    if not need:
        return
    hook = os.environ.get("GROKBOT_WEBHOOK_URL", "").lstrip("﻿").strip()
    if not hook:
        print("::warning::runner down with pending jobs, but GROKBOT_WEBHOOK_URL is not set")
        return
    gpu = "T4"
    for p in (LAB / "queue").glob("*.json"):
        if json.loads(p.read_text(encoding="utf-8"))["spec"].get("gpu") == "L4":
            gpu = "L4"
    body = {"event": "job_queued", "reason": "runner_stale" if running else "pending_jobs",
            "pending": len(queued) + len(running), "gpu": gpu, "workers": need,
            "notebooks": [NOTEBOOKS[w] for w in need], "live_workers": sorted(live)}
    headers = {"Content-Type": "application/json"}
    auth = os.environ.get("GROKBOT_WEBHOOK_AUTH", "").lstrip("﻿").strip()
    if auth.lower().startswith("authorization:"):
        auth = auth.split(":", 1)[1].strip()                 # tolerate a copied "Authorization: ..." line
    if auth:
        headers["Authorization"] = auth                      # full header value as shown in grokbot's routine
    req = urllib.request.Request(hook, data=json.dumps(body).encode(), headers=headers)
    urllib.request.urlopen(req, timeout=30)
    print(f"pinged grokbot: {body['event']} ({body['reason']})")


if __name__ == "__main__":
    main()
