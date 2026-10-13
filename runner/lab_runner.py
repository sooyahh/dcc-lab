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
Multiple workers: each Colab notebook sets LAB_WORKER (colab-a / colab-b). A job left in running/ is
resumed before the queue. With max_workers 1, whichever known notebook is up adopts it.
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

import drive_io

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
DRIVE_FAIL_GIVE_UP_S = 180                # after this, stop refreshing the git heartbeat so a dead FUSE can be restarted
MAX_INTERRUPTIONS = 10                    # runtime-disconnect resumes allowed per job (separate from max_attempts)
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
_last_sync = 0.0
_last_res_log = 0.0
_drive_fail_since: float | None = None


def status(state: str, exp_id: str | None = None, force_git: bool = False, **extra) -> None:
    global _last_git_status, _last_sync, _last_res_log, _drive_fail_since
    hb = {"at": now(), "worker": WORKER, "state": state, "exp_id": exp_id, "gpu": gpu(), **resources(exp_id), **extra}
    if exp_id:
        age = drive_io.ckpt_age_min(RUN_ROOT / exp_id)
        if age is not None:
            hb["last_ckpt_age_min"] = round(age, 1)
    # Drive writes go through a subprocess. A multi-GB checkpoint copy can wedge FUSE;
    # an in-process write_text then blocks this thread forever and the heartbeat stops.
    drive_files = {
        f"heartbeat_{WORKER}.json": json.dumps(hb, ensure_ascii=False),
        "heartbeat.json": json.dumps(hb, ensure_ascii=False),   # last writer (legacy readers)
    }
    try:
        pending = len(list((LAB / "queue").glob("*.json"))) + len(list((LAB / "running").glob("*.json")))
        drive_files["queue_pending.json"] = json.dumps(
            {"at": hb["at"], "count": pending, "gpu": wanted_gpu()}, ensure_ascii=False)
    except Exception:
        pass
    res_name = res_line = None
    if time.time() - _last_res_log >= 300:
        res_name = f"resources_{WORKER}.jsonl"
        res_line = json.dumps(hb, ensure_ascii=False) + "\n"
    if drive_io.publish_status(DRIVE_LAB / "status", drive_files, res_name, res_line):
        _drive_fail_since = None
        if res_line is not None:
            _last_res_log = time.time()
    else:
        err = getattr(drive_io.publish_status, "last_error", "")
        log(f"Drive heartbeat 쓰기 실패: {err}")
        if _drive_fail_since is None:
            _drive_fail_since = time.time()
        if time.time() - _drive_fail_since >= DRIVE_FAIL_GIVE_UP_S:
            # A fresh git heartbeat would look healthy and stop the webhook from remounting Drive.
            log("Drive 쓰기가 3분 넘게 실패하여 git heartbeat는 갱신하지 않음")
            return
    if time.time() - _last_sync > 300:                    # a busy worker never claims, so refresh the queue view here
        _last_sync = time.time()
        try:
            sync()
        except Exception as exc:
            log(f"큐 갱신 실패: {redact(str(exc))}")
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
            cu_text = drive_io.read_text(cu)
            if cu_text is not None:
                files["colab_cu.json"] = cu_text
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


def resources(exp_id: str | None) -> dict:
    """RAM / local disk. Checkpoint age is a Drive stat, probed from status() so this never touches Drive."""
    info: dict = {}
    try:
        import psutil  # type: ignore
        vm = psutil.virtual_memory()
        info.update(ram_used_gb=round((vm.total - vm.available) / 2**30, 1), ram_total_gb=round(vm.total / 2**30, 1))
    except Exception:
        pass
    try:
        du = shutil.disk_usage("/content")
        info["disk_free_gb"] = round(du.free / 2**30, 1)
    except Exception:
        pass
    return info


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


GPU_RANK = {"none": 0, "T4": 1, "L4": 2, "A100": 3, "H100": 4}


def gpu_rank(name: str) -> int:
    n = str(name).upper()
    return next((r for k, r in sorted(GPU_RANK.items(), key=lambda kv: -kv[1]) if k.upper() in n), 0)


def gpu_ok(want: str) -> bool:
    """A job runs on its GPU or a bigger one (T4 < L4 < A100 < H100); spec gpu is the minimum."""
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
def max_workers() -> int:
    try:
        return int(json.loads((LAB / "config.json").read_text(encoding="utf-8")).get("max_workers", 1))
    except Exception:
        return 1


def adopts_running(worker: str, owner: str | None, n_workers: int) -> bool:
    """Whether this notebook should continue a job left in running/.

    max_workers is 1, so only one GPU session exists. That session must pick up a job
    whose runtime was deleted (colab-b resumes colab-a's M2-SSL-005). It must not be
    limited to colab-a, or the job sits in running/ while the live worker drains the queue.
    """
    if owner == worker:
        return True
    if n_workers <= 1 and worker in KNOWN_WORKERS:
        return True
    return owner not in KNOWN_WORKERS and worker == KNOWN_WORKERS[0]


def claim_next() -> dict | None:
    sync()
    n_workers = max_workers()
    for p in sorted((LAB / "running").glob("*.json")):
        w = json.loads(p.read_text(encoding="utf-8")).get("worker")
        if adopts_running(WORKER, w, n_workers):
            job = {"_name": p.name, **json.loads(p.read_text(encoding="utf-8"))}
            if w != WORKER:
                job["worker"] = WORKER
                update_running(p.name, worker=WORKER)
            return job
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


def describe_ckpt(exp_id: str, root: Path | None = None) -> str:
    """One line for run.log: whether a resume file is already on Drive."""
    root = RUN_ROOT if root is None else root
    try:
        ckpts = list((root / exp_id).rglob("ckpt_last.pt"))
    except OSError as exc:
        return f"ckpt_last.pt 확인 실패: {exc}"
    if not ckpts:
        return "ckpt_last.pt 없음 (스크립트가 처음부터 학습)"
    ck = max(ckpts, key=lambda p: p.stat().st_mtime)
    age = (time.time() - ck.stat().st_mtime) / 60
    return (f"ckpt_last.pt 있음: {ck} size={ck.stat().st_size / 2**30:.2f}GB age={age:.1f}min "
            "(같은 명령이 이 파일을 읽으면 이어서 학습. attempt는 끊김이 나도 1로 남고 interruptions만 증가)")


_PY_ASSIGN = re.compile(r"""(^|[\s;&|])PYTHONPATH=("[^"]*"|'[^']*'|\S+)""")


def inject_runner_on_pythonpath(cmd: str, runner_dir: str) -> str:
    """Keep the runner dir on PYTHONPATH when the job command assigns it.

    `PYTHONPATH=src python ...` replaces the inherited value, so sitecustomize
    (Drive copy hook, safetensors redirect) would never load.
    """
    def repl(m: re.Match[str]) -> str:
        raw = m.group(2)
        if len(raw) >= 2 and raw[0] in "\"'" and raw[-1] == raw[0]:
            val = raw[1:-1]
            q = raw[0]
            merged = runner_dir if not val else runner_dir + os.pathsep + val
            return f"{m.group(1)}PYTHONPATH={q}{merged}{q}"
        merged = runner_dir if not raw else runner_dir + os.pathsep + raw
        return f"{m.group(1)}PYTHONPATH={merged}"
    return _PY_ASSIGN.sub(repl, cmd, count=1)


def describe_ckpt_bounded(exp_id: str, timeout: float = 30) -> str:
    """describe_ckpt on a daemon thread. A stuck Drive stat must not block job start."""
    box: dict[str, str] = {}

    def run() -> None:
        try:
            box["line"] = describe_ckpt(exp_id)
        except Exception as exc:
            box["line"] = f"ckpt_last.pt 확인 실패: {exc}"

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return "ckpt_last.pt 확인 시간 초과 (Drive 응답 없음)"
    return box.get("line", "ckpt_last.pt 확인 실패")


def build_child_env(repo: Path, exp_id: str, out: Path, work: Path, data_root: str | None,
                    base: dict[str, str]) -> dict[str, str]:
    """Env for the experiment process. Runner dir is on PYTHONPATH so sitecustomize runs."""
    env = {k: v for k, v in base.items() if k not in ("DCC_LAB_TOKEN", "DCC_TEAM_TOKEN")}
    if data_root and "DCC_DATA_ROOT" not in env:
        env["DCC_DATA_ROOT"] = data_root
    runner_dir = str(Path(__file__).resolve().parent)
    env.update(LAB_EXP_ID=exp_id, LAB_OUT=str(out), LAB_WORK=str(work), DCC_RUN_ROOT=str(RUN_ROOT.parent),
               PYTHONUNBUFFERED="1", HF_HUB_DISABLE_XET="1",
               PYTHONPATH=os.pathsep.join(p for p in (runner_dir, str(repo / "src"), env.get("PYTHONPATH", "")) if p))
    return env


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
    prev = job.get("attempts", 0)
    if prev > 0:
        # a job still in running/ with attempts>0 means the previous runner vanished (runtime disconnect);
        # real failures go through finish() and leave running/. Count these separately, not as attempts.
        interruptions = job.get("interruptions", 0) + 1
        if interruptions > job.get("max_interruptions", MAX_INTERRUPTIONS):
            finish(job, "failed", reason=f"연결 끊김 재개 {interruptions - 1}회 초과", interruptions=interruptions - 1)
            return
        attempts = prev
    else:
        interruptions, attempts = 0, 1
        if attempts > job.get("max_attempts", 3):
            finish(job, "failed", reason="max_attempts 초과 (반복 중단/오류)")
            return
    update_running(job["_name"], attempts=attempts, interruptions=interruptions,
                   started_at=job.get("started_at") or now())
    job["attempts"], job["interruptions"] = attempts, interruptions

    out = RUN_ROOT / exp_id
    out.mkdir(parents=True, exist_ok=True)
    work = WORK_ROOT / exp_id
    work.mkdir(parents=True, exist_ok=True)
    try:
        repo = prepare_code(job)
    except Exception as exc:
        finish(job, "failed", reason=f"code: {redact(str(exc))}")
        return

    data_root = find_data_root()
    env = build_child_env(repo, exp_id, out, work, str(data_root) if data_root else None, dict(os.environ))
    cmd = (spec["command"].replace("$LAB_OUT", str(out)).replace("$LAB_WORK", str(work))
           .replace("$LAB_HOME", str(LAB)))                  # $LAB_HOME = this repo (shared helper scripts)
    cmd = inject_runner_on_pythonpath(cmd, str(Path(__file__).resolve().parent))
    budget_s = float(spec.get("budget_hours", 6)) * 3600
    log(f"{exp_id} 시작 (attempt {attempts}) commit={job['commit'][:7]}\n  $ {cmd}")
    status("running", exp_id, force_git=True, attempt=attempts)

    t0 = time.time()
    rc, over = 1, False
    # tqdm refreshes with \r. Reading those as lines is fine, but flushing each one to Drive
    # (the same FUSE the child is mmap-reading) wedges the runtime. Keep the log local and
    # append it to Drive from another thread.
    local_log = work / "_runner_run.log"
    drive_log = out / "run.log"
    from safetensors_local import append_log_mirror
    stop_mirror = threading.Event()

    def mirror_loop() -> None:
        off = 0
        while True:
            try:
                off = append_log_mirror(local_log, drive_log, off)
            except Exception as exc:
                log(f"run.log 미러 실패: {redact(str(exc))}")
            if stop_mirror.wait(15):
                try:
                    append_log_mirror(local_log, drive_log, off)
                except Exception as exc:
                    log(f"run.log 마지막 미러 실패: {redact(str(exc))}")
                return

    mirror = threading.Thread(target=mirror_loop, daemon=True)
    mirror_started = False
    try:
        with open(local_log, "a", encoding="utf-8", newline="\n") as lf:
            banner = f"===== attempt {attempts} {now()} {WORKER} commit={job['commit']} ====="
            note = describe_ckpt_bounded(exp_id)
            # The cell shows runner stdout. The banner used to be written only into the log file.
            log(banner)
            log(note)
            lf.write(f"\n{banner}\n{note}\n")
            lf.flush()
            mirror.start()
            mirror_started = True
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
                lf.flush()
    finally:
        stop_mirror.set()
        if mirror_started:
            mirror.join(timeout=20)
    elapsed = round((time.time() - t0) / 60, 1)
    metrics_p = out / "metrics.json"
    if rc == 0 and metrics_p.exists():
        finish(job, "done", elapsed_min=elapsed, metrics=json.loads(metrics_p.read_text(encoding="utf-8")))
    elif over:
        finish(job, "failed", reason="budget_hours 초과", elapsed_min=elapsed)
    else:
        reason = f"exit {rc}" + ("" if metrics_p.exists() else ", metrics.json 없음")
        tail_src = local_log if local_log.exists() else drive_log
        tail = tail_src.read_text(encoding="utf-8", errors="replace")[-3000:]
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
