"""Loaded when this directory is on sys.path.

The runner process finds it because its script lives here. Experiment commands
often set PYTHONPATH=src, which would hide this directory; lab_runner prepends
the runner dir onto that assignment before starting the child.
"""
def _load() -> None:
    import sys

    try:
        from drive_io import install as install_drive

        install_drive()
    except Exception as exc:
        print(f"[runner] drive copy hook skipped: {exc}", file=sys.stderr)
    try:
        from safetensors_local import install as install_st

        install_st()
    except Exception as exc:
        print(f"[runner] safetensors localize skipped: {exc}", file=sys.stderr)


_load()
