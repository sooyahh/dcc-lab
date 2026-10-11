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
import urllib.error
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
    rank = {"none": 0, "T4": 1, "L4": 2, "A100": 3}

    def want(job: dict) -> str:
        g = str(job["spec"].get("gpu", "T4"))
        return "none" if g.lower() == "none" else g.upper()

    def hb_rank(w: str) -> int:
        g = str(hbs.get(w, {}).get("gpu", "")).upper()
        return max((r for k, r in rank.items() if k != "none" and k in g), default=0)

    # 1) a running job whose worker is down must be resumed by that worker's notebook (legacy names -> colab-a),
    #    on the GPU the job asks for (a job moved to L4 restarts its worker on L4)
    need: dict[str, str] = {}
    for job in running.values():
        w = job.get("worker")
        w = w if w in WORKERS else WORKERS[0]
        if w not in live and w not in need:
            need[w] = want(job)
    # 2) queued jobs that idle live workers cannot take (busy, or GPU too small) -> start more workers, up to max_workers
    busy = {job.get("worker") for job in running.values()}
    idle_live = [w for w in live if w not in busy]
    leftover = []
    for job in sorted((json.loads((LAB / "queue" / n).read_text(encoding="utf-8")) for n in queued),
                      key=lambda j: -rank.get(want(j), 1)):
        fit = next((w for w in idle_live if hb_rank(w) >= rank.get(want(job), 1)), None)
        if fit:
            idle_live.remove(fit)
        else:
            leftover.append(want(job))
    for w in WORKERS[:max_workers]:
        if not leftover:
            break
        if w not in live and w not in need and w not in busy:
            need[w] = leftover.pop(0)
    print(f"queued={len(queued)} running={len(running)} live={sorted(live)} need={need}")
    if not need:
        return
    hook = os.environ.get("GROKBOT_WEBHOOK_URL", "").lstrip("﻿").strip()
    if not hook:
        print("::warning::runner down with pending jobs, but GROKBOT_WEBHOOK_URL is not set")
        return
    gpu = max(need.values(), key=lambda g: rank.get(g, 1))
    body = {"event": "job_queued", "reason": "runner_stale" if running else "pending_jobs",
            "pending": len(queued) + len(running), "gpu": gpu, "workers": list(need),
            "gpus": need, "notebooks": [NOTEBOOKS[w] for w in need], "live_workers": sorted(live)}
    headers = {"Content-Type": "application/json"}
    auth = os.environ.get("GROKBOT_WEBHOOK_AUTH", "").lstrip("﻿").strip()
    if auth.lower().startswith("authorization:"):
        auth = auth.split(":", 1)[1].strip()                 # tolerate a copied "Authorization: ..." line
    if auth:
        headers["Authorization"] = auth                      # full header value as shown in grokbot's routine
    req = urllib.request.Request(hook, data=json.dumps(body).encode(), headers=headers)
    try:
        urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as exc:                    # show grokbot's reason (body has no secrets of ours)
        print(f"::error::grokbot webhook HTTP {exc.code}: {exc.read()[:500].decode('utf-8', 'replace')}")
        raise
    print(f"pinged grokbot: {body['event']} ({body['reason']})")


if __name__ == "__main__":
    main()
