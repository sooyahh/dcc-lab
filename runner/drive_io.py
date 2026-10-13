"""Interruptible copies onto Google Drive FUSE.

A multi-GB shutil.copyfile (ckpt_last.pt is ~3.5GB) holds Colab's Drive FUSE for
the whole write. Other threads then block in uninterruptible Drive calls, so
heartbeat.json and run.log freeze while the UI still says Executing. The copy
runs in a short-lived subprocess: the caller waits with a per-chunk timeout and
can abandon a wedged chunk. No fsync (fsync on this FUSE is a known hang).
"""
from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

DRIVE_MARK = "/content/drive"
_INSTALLED = False

_COPY_WORKER_SRC = r"""
import json, os, sys
req = json.loads(sys.stdin.readline() or "")
src, dst = req["src"], req["dst"]
start, chunk = int(req["start"]), int(req["chunk"])
total = os.path.getsize(src)
try:
    if start <= 0:
        begin, mode = 0, "wb"
    else:
        have = os.path.getsize(dst) if os.path.exists(dst) else 0
        if have > total:
            raise OSError("partial larger than source (%s > %s)" % (have, total))
        if have < start:
            raise OSError("partial shorter than acked (%s < %s)" % (have, start))
        if have == total:
            sys.stdout.write(json.dumps({"ok": True, "size": have}) + "\n")
            sys.stdout.flush()
            raise SystemExit(0)
        begin, mode = have, "ab"
    limit = req.get("limit")
    stop = total if not limit else min(total, begin + int(limit))
    with open(src, "rb") as r, open(dst, mode) as w:
        r.seek(begin)
        done = begin
        while done < stop:
            buf = r.read(min(chunk, stop - done))
            if not buf:
                break
            w.write(buf)
            done += len(buf)
            sys.stdout.write(json.dumps({"progress": done, "total": total}) + "\n")
            sys.stdout.flush()
    sys.stdout.write(json.dumps({"ok": True, "size": done}) + "\n")
    sys.stdout.flush()
except SystemExit:
    raise
except Exception as exc:
    sys.stdout.write(json.dumps({"ok": False, "err": str(exc)}) + "\n")
    sys.stdout.flush()
"""

_REPLACE_WORKER_SRC = r"""
import json, os, sys
req = json.loads(sys.stdin.readline() or "")
try:
    os.replace(req["src"], req["dst"])
    sys.stdout.write(json.dumps({"ok": True}) + "\n")
except Exception as exc:
    sys.stdout.write(json.dumps({"ok": False, "err": str(exc)}) + "\n")
sys.stdout.flush()
"""

_UNLINK_SRC = r"""
import os, sys
try:
    os.unlink(sys.argv[1])
except FileNotFoundError:
    pass
"""

_PUBLISH_SRC = r"""
import json, os, sys
spec = json.loads(sys.stdin.read() or "{}")
root = spec["root"]
os.makedirs(root, exist_ok=True)
for name, text in spec.get("files", {}).items():
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise SystemExit("bad name")
    path = os.path.join(root, name)
    tmp = path + ".tmpwrite"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)
line, rname = spec.get("resources_line"), spec.get("resources_name")
if line and rname and "/" not in rname and "\\" not in rname:
    with open(os.path.join(root, rname), "a", encoding="utf-8") as f:
        f.write(line)
"""

_CKPT_SRC = r"""
import os, sys, time
root = sys.argv[1]
newest = None
if os.path.isdir(root):
    for dirpath, _, names in os.walk(root):
        if "ckpt_last.pt" in names:
            p = os.path.join(dirpath, "ckpt_last.pt")
            try:
                m = os.stat(p).st_mtime
            except OSError:
                continue
            if newest is None or m > newest:
                newest = m
if newest is None:
    sys.stdout.write("none\n")
else:
    sys.stdout.write(str((time.time() - newest) / 60) + "\n")
"""

_READ_SRC = r"""
import os, sys
p = sys.argv[1]
if not os.path.exists(p):
    raise SystemExit(2)
sys.stdout.buffer.write(open(p, "rb").read())
"""

_APPEND_SRC = r"""
import os, sys
local, drive, offset = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.makedirs(os.path.dirname(drive) or ".", exist_ok=True)
copied = 0
with open(local, "rb") as src, open(drive, "ab") as dst:
    src.seek(offset)
    while True:
        buf = src.read(1 << 20)
        if not buf:
            break
        dst.write(buf)
        copied += len(buf)
sys.stdout.write(str(offset + copied) + "\n")
"""


def _log(msg: str) -> None:
    print(f"[runner] {msg}", flush=True)


def drive_mark() -> str:
    return os.environ.get("LAB_DRIVE_MARK", DRIVE_MARK)


def on_drive(path: str | os.PathLike[str]) -> bool:
    return drive_mark() in str(path)


def _min_bytes() -> int:
    return int(os.environ.get("LAB_DRIVE_COPY_MIN", str(64 << 20)))


def _chunk_bytes() -> int:
    return int(os.environ.get("LAB_DRIVE_CHUNK_BYTES", str(8 << 20)))


def _chunk_timeout() -> float:
    return float(os.environ.get("LAB_DRIVE_CHUNK_TIMEOUT", "60"))


_helper_lock = threading.Lock()
_wedged: subprocess.Popen[bytes] | None = None


def _close_pipes(proc: subprocess.Popen[bytes]) -> None:
    for stream in (proc.stdin, proc.stdout, proc.stderr):
        if stream is not None and not stream.closed:
            try:
                stream.close()
            except OSError:
                pass


def _run(code: str, timeout: float, input_bytes: bytes | None = None,
         args: list[str] | None = None) -> subprocess.CompletedProcess[bytes]:
    """python -S so the child does not import sitecustomize (no patched shutil).

    Do not use subprocess.run. After a timeout it SIGKILLs and then wait()s with
    no deadline. A helper blocked in a Drive FUSE syscall (D-state) ignores
    SIGKILL, so that wait never returns and the heartbeat thread stops for good.
    The webhook then restarts a runtime that is still training.
    """
    global _wedged
    with _helper_lock:
        if _wedged is not None:
            if _wedged.poll() is None:
                raise TimeoutError("previous drive helper still wedged")
            _wedged = None
        proc = subprocess.Popen(
            [sys.executable, "-S", "-c", code, *(args or [])],
            stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            try:
                out, err = proc.communicate(input_bytes, timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                _kill(proc)
                if proc.poll() is None:
                    _wedged = proc
                raise TimeoutError("drive helper timeout") from exc
            return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)
        finally:
            _close_pipes(proc)


class _LineReader:
    def __init__(self, proc: subprocess.Popen[bytes]) -> None:
        self.proc = proc
        self.buf = bytearray()

    def readline(self, timeout: float) -> str:
        assert self.proc.stdout is not None
        fd = self.proc.stdout.fileno()
        deadline = time.monotonic() + timeout
        while b"\n" not in self.buf:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("drive worker silent")
            ready, _, _ = select.select([fd], [], [], remaining)
            if not ready:
                raise TimeoutError("drive worker silent")
            chunk = os.read(fd, 65536)
            if not chunk:
                raise OSError("drive worker exited")
            self.buf.extend(chunk)
        line, _, rest = self.buf.partition(b"\n")
        self.buf = bytearray(rest)
        return line.decode()


def _popen(code: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-S", "-c", code],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0,
    )


def _send(proc: subprocess.Popen[bytes], obj: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(obj).encode() + b"\n")
    proc.stdin.flush()


def _kill(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is None:
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
    else:
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
    _close_pipes(proc)


def _cache_min() -> int:
    return int(os.environ.get("LAB_DRIVE_CACHE_MIN", str(512 << 20)))


def _span_bytes() -> int:
    """Close the Drive fd after this many bytes so one stuck read does not cover the whole zip."""
    return int(os.environ.get("LAB_DRIVE_SPAN_BYTES", str(1 << 30)))


def cache_path(src: str, total: int) -> Path | None:
    """Shared local copy of a large Drive file, reused by later jobs on this VM.

    /content is wiped when the runtime dies, so this only skips a second copy
    in the same VM (and a retry that finds the bytes still on disk).
    """
    if not on_drive(src) or total < _cache_min():
        return None
    root = os.environ.get("LAB_WORK", "").strip()
    if not root:
        return None
    name = Path(src).name
    if name.endswith(".tmp"):
        name = name[:-4]
    return Path(root).parent / "_drive_cache" / f"{name}.{total}"


def remember_cache(src: str, dst: str, total: int) -> None:
    path = cache_path(src, total)
    if path is None or os.path.abspath(dst) == os.path.abspath(path):
        return
    try:
        if path.exists() and path.stat().st_size == total:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        os.link(dst, path)
    except OSError:
        pass


def _unlink(path: str) -> None:
    try:
        _run(_UNLINK_SRC, 15, args=[path])
    except Exception:
        pass


def _partial_start(dst: str, total: int) -> int:
    """Bytes already on disk. A full file is returned as `total` so the copy is skipped."""
    if not os.path.exists(dst):
        return 0
    have = os.path.getsize(dst)
    if have == total:
        return total
    if have <= 0 or have > total:
        return 0
    return have


def copy_onto_drive(src: str | os.PathLike[str], dst: str | os.PathLike[str], *,
                    chunk: int | None = None, chunk_timeout: float | None = None,
                    attempts: int = 3) -> None:
    """Copy src to dst in chunks. Raise OSError so the experiment's own retry runs.

    A timed-out chunk is killed from here (the wait is interruptible). Bytes already
    written stay on disk, so the script's 2/4/8/16/32s retry continues instead of
    starting the 32GB zip over. A file read from Drive is closed and reopened every
    1 GiB. A finished copy is hardlinked into LAB_WORK's sibling `_drive_cache` so
    the next job on this VM does not read it from Drive again.
    """
    origin, dst_s = str(src), str(dst)
    total = os.path.getsize(origin)
    cached = cache_path(origin, total)
    src_s = origin
    if cached is not None and cached.exists() and cached.stat().st_size == total and os.path.abspath(cached) != os.path.abspath(dst_s):
        _log(f"로컬 캐시 사용 {cached.name}")
        src_s = str(cached)
    chunk = _chunk_bytes() if chunk is None else chunk
    chunk_timeout = _chunk_timeout() if chunk_timeout is None else chunk_timeout
    start = _partial_start(dst_s, total)
    if start == total:
        _log(f"이미 받음 {Path(dst_s).name} ({total / 2**20:.0f} MiB)")
        remember_cache(origin, dst_s, total)
        return
    last_err = "timeout"
    logged = start // (1 << 30)
    limit = _span_bytes() if on_drive(src_s) else 0
    chunk_s = f"{chunk / 2**20:.0f} MiB" if chunk >= 1 << 20 else f"{chunk} B"
    _log(f"청크 복사 시작 {Path(dst_s).name} ({start / 2**20:.0f}/{total / 2**20:.0f} MiB, {chunk_s} chunks)")
    fails = 0
    while fails < max(1, attempts):
        on_disk = _partial_start(dst_s, total)
        if on_disk >= total:
            _log(f"이미 받음 {Path(dst_s).name} ({total / 2**20:.0f} MiB)")
            remember_cache(origin, dst_s, total)
            return
        if start > on_disk:
            start = on_disk
        proc = _popen(_COPY_WORKER_SRC)
        reader = _LineReader(proc)
        try:
            payload = {"src": src_s, "dst": dst_s, "start": start, "chunk": chunk}
            if limit:
                payload["limit"] = limit
            _send(proc, payload)
            while True:
                msg = json.loads(reader.readline(chunk_timeout))
                if "progress" in msg:
                    start = int(msg["progress"])
                    step = start // (1 << 30)
                    if step != logged:
                        logged = step
                        _log(f"청크 복사 {start / 2**20:.0f}/{total / 2**20:.0f} MiB {Path(dst_s).name}")
                    continue
                if msg.get("ok"):
                    acked = int(msg.get("size", on_disk))
                    written = _partial_start(dst_s, total)
                    finished = acked >= total and (written >= total or not on_drive(dst_s))
                    if finished and written < total:
                        start = written
                        last_err = f"size {written} after ack {acked}"
                        fails += 1
                    elif finished:
                        _log(f"청크 복사 완료 {Path(dst_s).name} ({total / 2**20:.0f} MiB)")
                        remember_cache(origin, dst_s, total)
                        return
                    elif written > on_disk:
                        start = written
                        fails = 0
                    else:
                        last_err = "copy made no progress"
                        fails += 1
                    break
                last_err = str(msg.get("err", "copy failed"))
                fails += 1
                break
        except TimeoutError:
            last_err = f"chunk timeout at {start}/{total}"
            fails += 1
        except (OSError, json.JSONDecodeError) as exc:
            last_err = str(exc)
            fails += 1
        finally:
            _kill(proc)
    if _partial_start(dst_s, total) <= 0:
        _unlink(dst_s)
    raise OSError(f"Drive 복사 실패 {Path(origin).name} -> {Path(dst_s).name} ({last_err})")


def replace_on_drive(src: str | os.PathLike[str], dst: str | os.PathLike[str], *,
                     timeout: float = 30, attempts: int = 3) -> None:
    last = "timeout"
    for _ in range(max(1, attempts)):
        proc = _popen(_REPLACE_WORKER_SRC)
        try:
            _send(proc, {"src": str(src), "dst": str(dst)})
            msg = json.loads(_LineReader(proc).readline(timeout))
            if msg.get("ok"):
                return
            last = str(msg.get("err", "replace failed"))
        except TimeoutError:
            last = "replace timeout"
        except (OSError, json.JSONDecodeError) as exc:
            last = str(exc)
        finally:
            _kill(proc)
    raise OSError(f"Drive replace 실패 {src} -> {dst} ({last})")


def publish_status(root: str | os.PathLike[str], files: dict[str, str],
                   resources_name: str | None = None, resources_line: str | None = None,
                   timeout: float = 20) -> bool:
    """Write small status files. False on timeout or error; never raises."""
    payload = {"root": str(root), "files": files, "resources_name": resources_name,
               "resources_line": resources_line}
    try:
        proc = _run(_PUBLISH_SRC, timeout, json.dumps(payload).encode())
    except TimeoutError:
        publish_status.last_error = "timeout"  # type: ignore[attr-defined]
        return False
    if proc.returncode != 0:
        publish_status.last_error = proc.stderr.decode(errors="replace")[:200]  # type: ignore[attr-defined]
        return False
    return True


def ckpt_age_min(directory: str | os.PathLike[str], timeout: float = 15) -> float | None:
    try:
        proc = _run(_CKPT_SRC, timeout, args=[str(directory)])
    except TimeoutError:
        return None
    if proc.returncode != 0:
        return None
    text = proc.stdout.decode().strip()
    if not text or text == "none":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_text(path: str | os.PathLike[str], timeout: float = 15) -> str | None:
    try:
        proc = _run(_READ_SRC, timeout, args=[str(path)])
    except TimeoutError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode(errors="replace")


def append_file(local: str | os.PathLike[str], drive: str | os.PathLike[str], offset: int,
                timeout: float = 15) -> int:
    try:
        proc = _run(_APPEND_SRC, timeout, args=[str(local), str(drive), str(offset)])
    except TimeoutError as exc:
        raise TimeoutError("run.log mirror timeout") from exc
    if proc.returncode != 0:
        err = proc.stderr.decode(errors="replace")[:300]
        raise OSError(err or f"append exit {proc.returncode}")
    return int(proc.stdout.decode().strip())


def install() -> None:
    """Patch shutil.copyfile / os.replace / os.rename for large Drive files. Idempotent."""
    global _INSTALLED
    if _INSTALLED:
        return
    orig_copyfile = shutil.copyfile
    orig_replace = os.replace
    orig_rename = os.rename

    def copyfile(src, dst, *, follow_symlinks=True):
        if not follow_symlinks:
            try:
                if os.path.islink(src):
                    return orig_copyfile(src, dst, follow_symlinks=False)
            except OSError:
                return orig_copyfile(src, dst, follow_symlinks=follow_symlinks)
        try:
            size = os.path.getsize(src)
        except OSError:
            return orig_copyfile(src, dst, follow_symlinks=follow_symlinks)
        if size >= _min_bytes() and (on_drive(src) or on_drive(dst)):
            copy_onto_drive(src, dst)
            return dst
        return orig_copyfile(src, dst, follow_symlinks=follow_symlinks)

    def replace(src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        if src_dir_fd is None and dst_dir_fd is None and (on_drive(src) or on_drive(dst)):
            replace_on_drive(src, dst)
            return None
        return orig_replace(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    def rename(src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        if src_dir_fd is None and dst_dir_fd is None and (on_drive(src) or on_drive(dst)):
            replace_on_drive(src, dst)
            return None
        return orig_rename(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    shutil.copyfile = copyfile
    os.replace = replace
    os.rename = rename
    _INSTALLED = True
    _log("Drive 대용량 복사 훅 설치 (청크 복사, fsync 없음)")
