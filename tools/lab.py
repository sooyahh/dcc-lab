"""dcc-lab controller (runs locally now; the same commands run in GitHub Actions later).

    python tools/lab.py new M2-SSL-001 --mission 2 --title "..."   # specs/<EXP>.json skeleton
    python tools/lab.py submit M2-SSL-001 [--skip-review] [--force] # queue/<pri>_<EXP>.json, push, ping grokbot
    python tools/lab.py status                                      # queue + runner heartbeat + Colab CU
    python tools/lab.py collect M2-SSL-001                          # result + experiment_log row draft

Team repo location: env TEAM_REPO_DIR (default: ../01_prelim/dcc2026-prelim next to this repo).
Local-only settings (never committed): config.local.json  {"grokbot_webhook_url": "..."}
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
CFG = json.loads((LAB / "config.json").read_text(encoding="utf-8"))
LOCAL = LAB / "config.local.json"
LOCAL_CFG = json.loads(LOCAL.read_text(encoding="utf-8")) if LOCAL.exists() else {}
TEAM = Path(os.environ.get("TEAM_REPO_DIR", LAB.parent / "01_prelim" / "dcc2026-prelim"))
SPECS = LAB / "specs"
KST = dt.timezone(dt.timedelta(hours=9))
REQUIRED = ["exp_id", "mission", "title", "hypothesis", "branch", "command",
            "success_criteria", "uses_official_val", "budget_hours"]


def die(msg: str) -> None:
    print(f"[lab] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def git(repo: Path, *args: str, check: bool = True) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    if check and p.returncode != 0:
        die(f"git {' '.join(args)}: {p.stderr.strip()}")
    return p.stdout.strip()


def load_spec(exp_id: str) -> dict:
    p = SPECS / f"{exp_id}.json"
    if not p.is_file():
        die(f"spec 없음: {p}")
    spec = json.loads(p.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if spec.get(k) in (None, "")]
    if missing:
        die(f"spec 필수 항목 누락: {missing}")
    return spec


def remote_commit(spec: dict) -> str:
    """The commit must exist on the team repo's origin (Colab fetches it from GitHub)."""
    git(TEAM, "fetch", "-q", "origin", spec["branch"])
    ref = spec.get("commit") or f"origin/{spec['branch']}"
    sha = git(TEAM, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if not git(TEAM, "branch", "-r", "--contains", sha):
        die(f"{sha[:7]}이 origin에 없음. push 먼저")
    return sha


def jobs(folder: str) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((LAB / folder).glob("*.json"))]


def push(message: str) -> None:
    git(LAB, "add", "-A")
    git(LAB, "commit", "-q", "-m", message)
    for _ in range(3):
        if subprocess.run(["git", "-C", str(LAB), "push", "-q"], capture_output=True).returncode == 0:
            return
        git(LAB, "pull", "-q", "--rebase")
    die("push 실패")


def write_drive_pending() -> None:
    """Tell grokbot (via Drive) whether jobs are waiting. Works when Drive for desktop is mounted."""
    drive = Path(LOCAL_CFG.get("drive_lab_local", "G:/내 드라이브/dcc_lab"))
    if not drive.exists():
        return
    pending = jobs("queue") + jobs("running")
    gpus = [j["spec"].get("gpu", "T4") for j in pending]
    (drive / "status").mkdir(parents=True, exist_ok=True)
    (drive / "status" / "queue_pending.json").write_text(json.dumps(
        {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "count": len(pending),
         "gpu": next((g for g in ("A100", "L4") if g in gpus), "T4")}, ensure_ascii=False), encoding="utf-8")


def ping_grokbot(event: str, **data) -> None:
    hook = LOCAL_CFG.get("grokbot_webhook_url") or os.environ.get("GROKBOT_WEBHOOK_URL")
    if not hook:
        print("[lab] grokbot 웹훅 미설정 — Colab 러너가 꺼져 있으면 grokbot 예약 점검 때 시작됨")
        return
    body = json.dumps({"event": event, **data}, ensure_ascii=False).encode()
    headers = {"Content-Type": "application/json"}
    auth = LOCAL_CFG.get("grokbot_webhook_auth") or os.environ.get("GROKBOT_WEBHOOK_AUTH")
    if auth:
        headers["Authorization"] = auth.strip()
    req = urllib.request.Request(hook, data=body, headers=headers)
    try:
        urllib.request.urlopen(req, timeout=20)
        print(f"[lab] grokbot 웹훅 전송: {event}")
    except Exception as exc:
        print(f"[lab] grokbot 웹훅 실패(무시): {exc}")


# ------------------------------------------------------------------ commands
def cmd_new(a) -> None:
    p = SPECS / f"{a.exp_id}.json"
    if p.exists():
        die(f"이미 있음: {p}")
    spec = {
        "exp_id": a.exp_id, "mission": a.mission, "title": a.title,
        "hypothesis": "", "change_vs_baseline": "",
        "baseline": {"exp_id": "", "metric": "", "value": None},
        "branch": f"sooyah/lab-{a.exp_id.lower()}", "commit": "",
        "command": "python scripts/lab/<script>.py --out_dir $LAB_OUT",
        "uses_official_val": False, "success_criteria": "",
        "gpu": "T4", "budget_hours": CFG["default_budget_hours"], "priority": 5, "notes": "",
    }
    SPECS.mkdir(exist_ok=True)
    p.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(p)


def cmd_submit(a) -> None:
    git(LAB, "pull", "-q", "--rebase")
    spec = load_spec(a.exp_id)
    t = dt.datetime.now(KST)
    if t > dt.datetime.fromisoformat(CFG["freeze_at"]) and not a.force:
        die(f"동결({CFG['freeze_at']}) 이후 제출 금지. 꼭 필요하면 --force")
    commit = remote_commit(spec)
    review = LAB / "reviews" / f"{a.exp_id}_{commit[:7]}.md"
    if not a.skip_review and ("VERDICT: PASS" not in (review.read_text(encoding="utf-8") if review.exists() else "")):
        die(f"{commit[:7]}의 PASS 검토 없음 ({review.relative_to(LAB)})")
    if spec["uses_official_val"]:
        used = sum(1 for j in jobs("done") if j["spec"]["mission"] == spec["mission"] and j["spec"]["uses_official_val"])
        if used >= CFG["official_val_budget_per_mission"] and not a.force:
            die(f"M{spec['mission']} 공식 Val 예산 소진({used}). 최종 후보만 --force")
    for folder in ("queue", "running"):
        if any(j["spec"]["exp_id"] == a.exp_id for j in jobs(folder)):
            die(f"이미 {folder}/ 에 있음")
    job = {"spec": spec, "commit": commit, "submitted_at": t.isoformat(timespec="seconds"),
           "attempts": 0, "max_attempts": CFG["max_attempts"]}
    name = f"{int(spec.get('priority', 5)):02d}_{a.exp_id}.json"
    (LAB / "queue").mkdir(exist_ok=True)
    (LAB / "queue" / name).write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    push(f"queue {a.exp_id} @ {commit[:7]}")
    print(f"[lab] 큐 등록: {name}  commit={commit[:7]}")
    write_drive_pending()
    ping_grokbot("job_queued", exp_id=a.exp_id)


def cmd_status(a) -> None:
    git(LAB, "pull", "-q", "--rebase")
    for folder in ("queue", "running", "done", "failed"):
        names = [j["spec"]["exp_id"] for j in jobs(folder)]
        print(f"{folder:8s} {len(names):3d}  {', '.join(names[-8:])}")
    git(LAB, "fetch", "-q", "origin", "status", check=False)
    names = git(LAB, "ls-tree", "--name-only", "origin/status", check=False).split()
    for f in sorted(n for n in names if n.startswith("heartbeat_")) + ["colab_cu.json"]:
        txt = git(LAB, "show", f"origin/status:{f}", check=False)
        if not txt:
            print(f"{f}: 없음")
            continue
        d = json.loads(txt)
        age = ""
        if "at" in d:
            sec = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(d["at"])).total_seconds()
            age = f" ({int(sec // 60)}분 전{', STALE' if sec > 40 * 60 and d.get('state') == 'running' else ''})"
        print(f"{f}: {json.dumps(d, ensure_ascii=False)}{age}")


def cmd_collect(a) -> None:
    git(LAB, "pull", "-q", "--rebase")
    hits = [j for f in ("done", "failed") for j in jobs(f) if j["spec"]["exp_id"] == a.exp_id]
    if not hits:
        die("결과 없음")
    r = max(hits, key=lambda j: j.get("finished_at") or "")
    s, m = r["spec"], r.get("metrics") or {}
    pm = m.get("primary_metric") or {}
    print(json.dumps(r, ensure_ascii=False, indent=2))
    res = f"{pm.get('name')} {pm.get('value')} ({pm.get('split')})" if pm else r.get("reason", r["status"])
    print("\n--- experiment_log.md 행 초안 ---")
    print(f"| {s['exp_id']} | {(r.get('finished_at') or '')[:10]} | {s['title']} (commit `{r['commit'][:7]}`, "
          f"seed {m.get('seed', '?')}, {r.get('gpu', '?')}, {r.get('elapsed_min', '?')}분) | {res} | "
          f"{'완료' if r['status'] == 'done' else '실패'} | Drive `dcc_runs/lab/{s['exp_id']}/` |")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new"); p.add_argument("exp_id"); p.add_argument("--mission", type=int, required=True)
    p.add_argument("--title", required=True); p.set_defaults(fn=cmd_new)
    p = sub.add_parser("submit"); p.add_argument("exp_id")
    p.add_argument("--skip-review", action="store_true"); p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_submit)
    p = sub.add_parser("status"); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("collect"); p.add_argument("exp_id"); p.set_defaults(fn=cmd_collect)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
