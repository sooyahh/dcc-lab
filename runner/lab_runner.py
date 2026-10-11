"""Colab GPU worker for sooyahh/dcc-lab.

Started by runner/lab_worker.ipynb (grokbot opens it and presses Run all):
    python /content/dcc-lab/runner/lab_runner.py --idle-exit-min 30

Queue protocol (dcc-lab repo, main branch):
    queue/<pri>_<EXP>.json  --claim-->  running/  --finish-->  done/ | failed/
    results/<EXP>/{metrics.json,run_tail.log}
Status: orphan branch `status` (force-pushed, one commit) + Drive MyDrive/dcc_lab/status/heartbeat.json
Code:   team repo checked out at job["commit"] (read-only token).
Outputs (ckpt etc.): Drive MyDrive/dcc_runs/lab/<EXP>/  -> survives runtime death, enables resume.

Experiment contract: see docs/implementer.md. Success = exit 0 AND $LAB_OUT/metrics.json.
Multiple workers: each Colab notebook sets LAB_WORKER (colab-a / colab-b). A job left in running/ with our
worker name is ours and is resumed first; other workers' jobs are left alone.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import unicodedata
from pathlib import Path

LAB_REPO = "sooyahh/dcc-lab"
TEAM_REPO = "eigensinn-dcc2026/prelim"
LAB = Path(os.environ.get("LAB_CLONE", "/content/dcc-lab"))
TEAM = Path(os.environ.get("TEAM_CLONE", "/content/team-repo"))
CODE_CACHE = Path(os.environ.get("LAB_CODE_CACHE", "/content/lab_code"))
WORK_ROOT = Path(os.environ.get("LAB_WORK_ROOT", "/content/lab_work"))
DRIVE_LAB = Path(os.environ.get("LAB_DRIVE_DIR", "/content/drive/MyDrive/dcc_lab"))
RUN_ROOT = Path(os.environ.get("LAB_RUN_ROOT", "/content/drive/MyDrive/dcc_runs/lab"))
WORKER = os.environ.get("LAB_WORKER", "colab-" + socket.gethostname()[:8])
KNOWN_WORKERS = ("colab-a", "colab-b")
GIT_STATUS_EVERY_S = 15 * 60
DATA_DIR = "대학부 데이터"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def log(msg: str) -> None:
    print(f"[runner {dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


USE_GIT_CREDENTIALS = bool(os.environ.get("LAB_USE_GIT_CREDENTIALS"))   # local dry runs: OS credential helper


# Fine-grained tokens are scoped to one owner, so two are needed:
#   lab  = sooyahh/dcc-lab, Contents read/write   (env DCC_LAB_TOKEN  or .secrets/github_token.txt)
#   team = eigensinn-dcc2026/prelim, Contents read (env DCC_TEAM_TOKEN or .secrets/github_team_token.txt)
SECRETS = {"lab": ("DCC_LAB_TOKEN", "github_token.txt"), "team": ("DCC_TEAM_TOKEN", "github_team_token.txt")}
TOKENS: dict[str, str] = {}


def load_tokens() -> None:
    if USE_GIT_CREDENTIALS:
        return
    for key, (env, fname) in SECRETS.items():
        tok = os.environ.get(env, "").strip()
        f = DRIVE_LAB / ".secrets" / fname
        if not tok and f.exists():
            tok = f.read_text(encoding="utf-8").strip()
        if not tok:
            raise SystemExit(f"GitHub 토큰 없음: env {env} 또는 MyDrive/dcc_lab/.secrets/{fname}")
        TOKENS[key] = tok


def redact(s: str) -> str:
    for tok in TOKENS.values():
        s = s.replace(tok, "***")
    return s


def git(repo: Path, *args: str, check: bool = True) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(redact(f"git {' '.join(args)} failed: {p.stderr.strip()}"))
    return p.stdout.strip()


def url(repo: str) -> str:
    if USE_GIT_CREDENTIALS:
        return f"https://github.com/{repo}.git"
    tok = TOKENS["lab" if repo == LAB_REPO else "team"]
    return f"https://x-access-token:{tok}@github.com/{repo}.git"


def ensure_clones() -> None:
    if not (LAB / ".git").exists():
        subprocess.run(["git", "clone", "-q", url(LAB_REPO), str(LAB)], check=True)
    if not (TEAM / ".git").exists():
        subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", url(TEAM_REPO), str(TEAM)],
                       check=True)
    for repo in (LAB, TEAM):
        git(repo, "remote", "set-url", "origin", url(LAB_REPO if repo == LAB else TEAM_REPO))
    git(LAB, "config", "user.name", "dcc-lab-runner")
    git(LAB, "config", "user.email", "dcc-lab-runner@users.noreply.github.com")


def sync() -> None:
    git(LAB, "fetch", "-q", "origin", "main")
    git(LAB, "reset", "-q", "--hard", "origin/main")   # runner keeps no local-only state in the clone


def commit_push(message: str, mutate) -> None:
    """Apply `mutate()` on fresh origin/main and push; retry on races with other writers."""
    for attempt in range(6):
        sync()
        mutate()
        git(LAB, "add", "-A")
        if not git(LAB, "status", "--porcelain"):
            return
        git(LAB, "commit", "-q", "-m", message)
        if subprocess.run(["git", "-C", str(LAB), "push", "-q", "origin", "HEAD:main"],
                          capture_output=True).returncode == 0:
            return
        time.sleep(3 + attempt * 5)
    raise RuntimeError(f"push 실패: {message}")


# ------------------------------------------------------------------ status
_last_git_status = 0.0


def status(state: str, exp_id: str | None = None, force_git: bool = False, **extra) -> None:
    global _last_git_status
    hb = {"at": now(), "worker": WORKER, "state": state, "exp_id": exp_id, "gpu": gpu(), **extra}
    (DRIVE_LAB / "status").mkdir(parents=True, exist_ok=True)
    for fname in (f"heartbeat_{WORKER}.json", "heartbeat.json"):      # heartbeat.json = last writer (legacy readers)
        (DRIVE_LAB / "status" / fname).write_text(json.dumps(hb, ensure_ascii=False), encoding="utf-8")
    pending = len(list((LAB / "queue").glob("*.json"))) + len(list((LAB / "running").glob("*.json")))
    (DRIVE_LAB / "status" / "queue_pending.json").write_text(
        json.dumps({"at": hb["at"], "count": pending, "gpu": wanted_gpu()}), encoding="utf-8")
    if not force_git and time.time() - _last_git_status < GIT_STATUS_EVERY_S:
        return
    hb_text = json.dumps(hb, ensure_ascii=False, indent=2)
    cu = DRIVE_LAB / "status" / "colab_cu.json"            # written by grokbot
    try:
        for attempt in range(4):
            # status branch is shared by all workers: keep the others' files, replace ours, push with a lease
            git(LAB, "fetch", "-q", "origin", "status", check=False)
            parent = git(LAB, "rev-parse", "-q", "--verify", "origin/status", check=False)
            files: dict[str, str] = {}
            if parent:
                for n in git(LAB, "ls-tree", "--name-only", parent).splitlines():
                    if n.startswith("heartbeat") or n == "colab_cu.json":
                        files[n] = git(LAB, "show", f"{parent}:{n}")
            files[f"heartbeat_{WORKER}.json"] = hb_text
            files["heartbeat.json"] = hb_text
            if cu.exists():
                files["colab_cu.json"] = cu.read_text(encoding="utf-8")
            entries = []
            for name, text in files.items():
                sha = subprocess.run(["git", "-C", str(LAB), "hash-object", "-w", "--stdin"], input=text.encode(),
                                     capture_output=True, check=True).stdout.decode().strip()
                entries.append(f"100644 blob {sha}\t{name}\n")
            tree = subprocess.run(["git", "-C", str(LAB), "mktree"], input="".join(entries).encode(),
                                  capture_output=True, check=True).stdout.decode().strip()   # bytes: no CRLF in names
            commit = git(LAB, "commit-tree", tree, "-m", f"status {WORKER} {state} {exp_id or ''}")
            lease = f"--force-with-lease=refs/heads/status:{parent}" if parent else "--force"
            if subprocess.run(["git", "-C", str(LAB), "push", "-q", lease, "origin", f"{commit}:refs/heads/status"],
                              capture_output=True).returncode == 0:
                _last_git_status = time.time()
                break
            time.sleep(2 + attempt * 3)
    except Exception as exc:                                 # status is best-effort
        log(f"status push 실패: {redact(str(exc))}")


_gpu = None


def gpu() -> str:
    global _gpu
    if _gpu is None:
        try:
            _gpu = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                                  capture_output=True, text=True, timeout=30).stdout.strip() or "none"
        except Exception:
            _gpu = "none"
    return _gpu


GPU_RANK = {"none": 0, "T4": 1, "L4": 2, "A100": 3}


def gpu_rank(name: str) -> int:
    n = str(name).upper()
    return next((r for k, r in sorted(GPU_RANK.items(), key=lambda kv: -kv[1]) if k.upper() in n), 0)


def gpu_ok(want: str) -> bool:
    """T4 jobs run on T4/L4/A100; L4 jobs need L4 or A100 (more GPU memory and system RAM)."""
    return gpu_rank(gpu()) >= GPU_RANK.get(str(want).upper() if str(want).lower() != "none" else "none", 1)


def wanted_gpu() -> str:
    """Biggest GPU any queued job asks for (grokbot picks the runtime type from this)."""
    wants = [json.loads(p.read_text(encoding="utf-8"))["spec"].get("gpu", "T4") for p in (LAB / "queue").glob("*.json")]
    return max(wants, key=lambda w: GPU_RANK.get(str(w).upper(), 1), default="T4")


def find_data_root() -> Path | None:
    """Official data folder (has Training/ and Validation/) on the mounted Drive, via shortcut or MyDrive."""
    drive = DRIVE_LAB.parent.parent                          # /content/drive
    for attempt in range(13):                                # shared-folder shortcuts can take a while to resolve
        try:
            os.listdir(drive / "MyDrive")                    # listing nudges the FUSE mount to resolve shortcuts
        except OSError:
            pass
        # Drive FUSE may return Hangul names in NFD; compare NFC-normalized names and use the real on-disk name
        def named(parent: Path) -> list[Path]:
            try:
                # also accept duplicate-shortcut names like "대학부 데이터 (1)"; Training/Validation check decides
                return [parent / n for n in sorted(os.listdir(parent))
                        if unicodedata.normalize("NFC", n).startswith(DATA_DIR)]
            except OSError:
                return []
        cands = named(drive / "MyDrive")
        sc = drive / ".shortcut-targets-by-id"
        for d in (sorted(sc.iterdir()) if sc.is_dir() else []):
            cands += named(d) + [q for sub in named(d) for q in named(sub)]
        for c in cands:
            for p in [c] + named(c):
                try:
                    if (p / "Training").is_dir() and (p / "Validation").is_dir():
                        return p
                except OSError:
                    pass
        if attempt < 12:
            log(f"데이터 폴더 대기 중 ({attempt + 1}/12)")
            time.sleep(10)
    return None


# ------------------------------------------------------------------ jobs
def claim_next() -> dict | None:
    sync()
    for p in sorted((LAB / "running").glob("*.json")):
        w = json.loads(p.read_text(encoding="utf-8")).get("worker")
        # ours; or a legacy hostname-named worker's job, adopted by colab-a
        if w == WORKER or (w not in KNOWN_WORKERS and WORKER == "colab-a"):
            return {"_name": p.name, **json.loads(p.read_text(encoding="utf-8"))}
    def runnable(p: Path) -> bool:                           # a job runs only on a GPU at least as big as it asks
        return gpu_ok(json.loads(p.read_text(encoding="utf-8"))["spec"].get("gpu", "T4"))

    queued = [p for p in sorted((LAB / "queue").glob("*.json")) if runnable(p)]
    if not queued:
        return None
    name = queued[0].name

    def mutate():
        src = LAB / "queue" / name
        if not src.exists():
            return
        job = json.loads(src.read_text(encoding="utf-8"))
        job.update(worker=WORKER, claimed_at=now())
        (LAB / "running").mkdir(exist_ok=True)
        (LAB / "running" / name).write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        src.unlink()

    commit_push(f"claim {name} by {WORKER}", mutate)
    p = LAB / "running" / name
    if not p.exists():
        return None
    job = json.loads(p.read_text(encoding="utf-8"))
    if job.get("worker") != WORKER:                          # lost the claim race to another worker
        return None
    return {"_name": name, **job}


def update_running(name: str, **fields) -> None:
    def mutate():
        p = LAB / "running" / name
        if p.exists():
            job = json.loads(p.read_text(encoding="utf-8"))
            job.update(fields)
            p.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    commit_push(f"update {name}", mutate)


def prepare_code(job: dict) -> Path:
    commit = job["commit"]
    dst = CODE_CACHE / commit[:12]
    if (dst / ".ready").exists():
        return dst
    git(TEAM, "fetch", "-q", "origin", job["spec"]["branch"], check=False)
    git(TEAM, "fetch", "-q", "origin", commit)
    shutil.rmtree(dst, ignore_errors=True)
    git(TEAM, "worktree", "prune")
    git(TEAM, "worktree", "add", "-q", "--detach", str(dst), commit)
    req = dst / "requirements.txt"
    if req.exists() and not os.environ.get("LAB_SKIP_PIP"):
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(req)], check=False)
    (dst / ".ready").write_text(commit)
    return dst


def finish(job: dict, state: str, **extra) -> None:
    name, exp_id = job["_name"], job["spec"]["exp_id"]
    out = RUN_ROOT / exp_id
    result = {k: v for k, v in job.items() if k != "_name"}
    result.update(status=state, worker=WORKER, gpu=gpu(), finished_at=now(), **extra)

    def mutate():
        folder = LAB / ("done" if state == "done" else "failed")
        folder.mkdir(exist_ok=True)
        (folder / name).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        (LAB / "running" / name).unlink(missing_ok=True)
        res = LAB / "results" / exp_id
        res.mkdir(parents=True, exist_ok=True)
        if (out / "metrics.json").exists():
            shutil.copy(out / "metrics.json", res / "metrics.json")
        if (out / "run.log").exists():
            tail = (out / "run.log").read_text(encoding="utf-8", errors="replace")[-20000:]
            (res / "run_tail.log").write_text(tail, encoding="utf-8")

    commit_push(f"{state} {exp_id}", mutate)
    status("idle", None, force_git=True, last=f"{state} {exp_id}")
    log(f"{exp_id}: {state} {extra.get('reason', '')}")


def run_job(job: dict) -> None:
    spec = job["spec"]
    exp_id = spec["exp_id"]
    attempts = job.get("attempts", 0) + 1
    if attempts > job.get("max_attempts", 3):
        finish(job, "failed", reason="max_attempts 초과 (반복 중단/오류)")
        return
    update_running(job["_name"], attempts=attempts, started_at=job.get("started_at") or now())
    job["attempts"] = attempts

    out = RUN_ROOT / exp_id
    out.mkdir(parents=True, exist_ok=True)
    work = WORK_ROOT / exp_id
    work.mkdir(parents=True, exist_ok=True)
    try:
        repo = prepare_code(job)
    except Exception as exc:
        finish(job, "failed", reason=f"code: {redact(str(exc))}")
        return

    env = {k: v for k, v in os.environ.items() if k not in ("DCC_LAB_TOKEN", "DCC_TEAM_TOKEN")}
    data_root = find_data_root()
    if data_root and "DCC_DATA_ROOT" not in env:
        env["DCC_DATA_ROOT"] = str(data_root)                # older team commits don't search Drive shortcuts
    env.update(LAB_EXP_ID=exp_id, LAB_OUT=str(out), LAB_WORK=str(work), DCC_RUN_ROOT=str(RUN_ROOT.parent),
               PYTHONUNBUFFERED="1",
               PYTHONPATH=os.pathsep.join([str(repo / "src"), os.environ.get("PYTHONPATH", "")]))
    cmd = (spec["command"].replace("$LAB_OUT", str(out)).replace("$LAB_WORK", str(work))
           .replace("$LAB_HOME", str(LAB)))                  # $LAB_HOME = this repo (shared helper scripts)
    budget_s = float(spec.get("budget_hours", 6)) * 3600
    log(f"{exp_id} 시작 (attempt {attempts}) commit={job['commit'][:7]}\n  $ {cmd}")
    status("running", exp_id, force_git=True, attempt=attempts)

    t0, over = time.time(), False
    with open(out / "run.log", "a", encoding="utf-8") as lf:
        lf.write(f"\n===== attempt {attempts} {now()} {WORKER} commit={job['commit']} =====\n")
        proc = subprocess.Popen(cmd, shell=True, cwd=repo, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1, start_new_session=True)
        state = {"over": False}

        def watch() -> None:
            # heartbeat + budget on a timer: a job may print nothing (or only \r progress bars) for a long time
            while proc.poll() is None:
                try:
                    status("running", exp_id, attempt=attempts)
                except Exception as exc:                     # never let the heartbeat kill the job
                    log(f"heartbeat 실패: {redact(str(exc))}")
                if time.time() - t0 > budget_s:
                    state["over"] = True
                    os.killpg(proc.pid, 9)                   # shell=True: kill the whole process group
                    return
                time.sleep(60)

        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        for line in proc.stdout:
            lf.write(line)
            lf.flush()
            sys.stdout.write(line)
        rc = proc.wait()
        watcher.join(timeout=5)
        over = state["over"]
        if over:
            lf.write("\n[runner] budget_hours 초과로 중단\n")
    elapsed = round((time.time() - t0) / 60, 1)
    metrics_p = out / "metrics.json"
    if rc == 0 and metrics_p.exists():
        finish(job, "done", elapsed_min=elapsed, metrics=json.loads(metrics_p.read_text(encoding="utf-8")))
    elif over:
        finish(job, "failed", reason="budget_hours 초과", elapsed_min=elapsed)
    else:
        reason = f"exit {rc}" + ("" if metrics_p.exists() else ", metrics.json 없음")
        tail = (out / "run.log").read_text(encoding="utf-8", errors="replace")[-3000:]
        oom = bool(re.search(r"CUDA out of memory|OutOfMemoryError", tail))
        finish(job, "failed", reason=reason + (" (OOM)" if oom else ""), elapsed_min=elapsed, log_tail=tail)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--idle-exit-min", type=float, default=30,
                    help="큐가 이 시간 동안 비면 종료 (컴퓨팅 단위 절약)")
    ap.add_argument("--unassign-on-idle", action="store_true", help="유휴 종료 시 런타임까지 해제")
    ap.add_argument("--max-jobs", type=int, default=0, help="이 개수만 처리하고 종료 (시험용, 0=무제한)")
    a = ap.parse_args()
    load_tokens()
    ensure_clones()
    log(f"worker={WORKER} gpu={gpu()}")
    status("idle", force_git=True)
    idle_since, done_jobs = time.time(), 0
    me = Path(__file__).resolve()
    my_code = me.read_bytes()
    while True:
        try:
            sync()
            if me.exists() and me.read_bytes() != my_code:   # self-update before claiming: no notebook restart needed
                log("러너 코드가 갱신되어 재시작")
                os.execv(sys.executable, [sys.executable, str(me), *sys.argv[1:]])
            job = claim_next()
        except Exception as exc:
            log(f"큐 확인 실패: {redact(str(exc))}")
            job = None
        if job is None:
            status("idle")
            if time.time() - idle_since > a.idle_exit_min * 60:
                log("큐가 비어 종료")
                status("stopped", force_git=True)
                if a.unassign_on_idle:
                    from google.colab import runtime  # type: ignore
                    runtime.unassign()
                return
            time.sleep(60)
            continue
        run_job(job)
        idle_since = time.time()
        done_jobs += 1
        if a.max_jobs and done_jobs >= a.max_jobs:
            status("stopped", force_git=True)
            return


if __name__ == "__main__":
    main()
