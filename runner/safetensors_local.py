"""Keep safetensors mmap off Google Drive.

Colab's Drive FUSE plus safetensors' default mmap kills the VM (no Python
traceback) while transformers prints "Loading weights". WavLM revisions that
only have pytorch_model.bin never hit this. Copy the file onto local disk
(LAB_WORK) and open that. If the copy fails, open the Drive file with pread.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import threading
from pathlib import Path

DRIVE_MARK = "/content/drive"
_LOCK = threading.Lock()
_INSTALLED = False


def _log(msg: str) -> None:
    print(f"[runner] {msg}", flush=True)


def localize_safetensors(filename: str | os.PathLike[str], drive_mark: str = DRIVE_MARK) -> str | None:
    """Copy a Drive .safetensors file into LAB_WORK. None means use the original path."""
    path = Path(filename)
    text = str(path)
    if drive_mark not in text or path.suffix != ".safetensors":
        return None
    work = os.environ.get("LAB_WORK", "").strip()
    if not work:
        return None
    try:
        src_stat = path.stat()
    except OSError as exc:
        _log(f"safetensors stat 실패 ({path.name}: {exc}); Drive 파일을 pread로 연다")
        return None
    digest = f"{path.parent.name}__{path.name}"
    dst_dir = Path(work) / "_safetensors_local"
    dst = dst_dir / digest
    with _LOCK:
        if dst.exists() and dst.stat().st_size == src_stat.st_size:
            return str(dst)
        dst_dir.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(dst.suffix + ".tmp")
        _log(f"safetensors Drive→로컬 복사 시작 {path.name} ({src_stat.st_size / 2**20:.0f} MiB)")
        try:
            from drive_io import copy_onto_drive

            # In a subprocess so a wedged Drive read does not freeze this process.
            copy_onto_drive(path, tmp)
            os.replace(tmp, dst)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            _log(f"safetensors 로컬 복사 실패 ({exc}); Drive 파일을 pread로 연다")
            return None
    _log(f"safetensors 로컬 복사 완료 {dst} ({src_stat.st_size / 2**20:.0f} MiB)")
    return str(dst)


def _redirect_open(original, filename, args, kwargs):
    local = localize_safetensors(filename)
    if local is not None:
        filename = local
    elif DRIVE_MARK in str(filename) and "backend" not in kwargs:
        kwargs = dict(kwargs)
        kwargs["backend"] = "pread"
    return original(filename, *args, **kwargs)


def _patch_torch_module(mod) -> None:
    """safetensors.torch binds safe_open at import. Patch that name too."""
    if getattr(mod, "_runner_safe_open", False):
        return
    original = mod.safe_open

    def safe_open(filename, *args, **kwargs):
        return _redirect_open(original, filename, args, kwargs)

    mod.safe_open = safe_open
    mod._runner_safe_open = True


class _TorchHook:
    def find_spec(self, fullname, path, target=None):
        if fullname != "safetensors.torch":
            return None
        if self in sys.meta_path:
            sys.meta_path.remove(self)
        try:
            spec = importlib.util.find_spec(fullname)
        finally:
            if self not in sys.meta_path:
                sys.meta_path.insert(0, self)
        if spec is None or spec.loader is None:
            return None
        loader = spec.loader
        orig_exec = loader.exec_module

        def exec_module(module, _orig=orig_exec, _loader=loader):
            _loader.exec_module = _orig
            _orig(module)
            _patch_torch_module(module)

        loader.exec_module = exec_module
        return spec


def install() -> None:
    """Patch safetensors.safe_open. Later `from safetensors import safe_open` sees it."""
    global _INSTALLED
    if _INSTALLED:
        return
    try:
        import safetensors
    except Exception as exc:
        _log(f"safetensors 없음, Drive mmap 회피 생략: {exc}")
        return
    original = safetensors.safe_open

    def safe_open(filename, *args, **kwargs):
        return _redirect_open(original, filename, args, kwargs)

    safetensors.safe_open = safe_open
    torch_mod = sys.modules.get("safetensors.torch")
    if torch_mod is not None:
        _patch_torch_module(torch_mod)
    if not any(isinstance(hook, _TorchHook) for hook in sys.meta_path):
        sys.meta_path.insert(0, _TorchHook())
    _INSTALLED = True


def append_log_mirror(local: Path, drive: Path, offset: int) -> int:
    """Append bytes of the local run log to the Drive copy. Returns the new offset.

    Drive appends go through a subprocess so a stuck FUSE write does not pin this thread.
    """
    if not local.exists():
        return offset
    size = local.stat().st_size
    if size < offset:
        offset = 0
    if size == offset:
        return offset
    from drive_io import append_file, on_drive

    if on_drive(drive):
        return append_file(local, drive, offset)
    drive.parent.mkdir(parents=True, exist_ok=True)
    with open(local, "rb") as src, open(drive, "ab") as dst:
        src.seek(offset)
        while True:
            buf = src.read(1 << 20)
            if not buf:
                break
            dst.write(buf)
        dst.flush()
    return size
