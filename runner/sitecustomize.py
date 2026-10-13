"""Loaded for experiment subprocesses because the runner puts this directory on PYTHONPATH."""
try:
    from safetensors_local import install

    install()
except Exception as exc:
    import sys

    print(f"[runner] safetensors localize skipped: {exc}", file=sys.stderr)
