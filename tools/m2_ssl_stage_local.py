"""Build M2-SSL-001's training sample locally, exactly as scripts/lab/m2_ssl_001.py:stage() would on Colab.

Needed because the Colab account's Drive has the official data only as zip parts (no extracted Training/).
stage() skips the data root when LAB_OUT already has `sample.json` + `training_sample.tar`, so we write those.
Same rules as the script (commit a0eb12a): rglob over <root>/Training, Seoul-only via is_seoul_path,
pair .wav/.json by stem, sorted stems, random.Random(42).sample(stems, 4000), tar arcname = path relative to root.

    python tools/m2_ssl_stage_local.py --root <dir with Training/> --team <team repo> --out <LAB_OUT on Drive>
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tarfile
from pathlib import Path

SEED = 42


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--team", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n-calls", type=int, default=4000)
    a = ap.parse_args()
    sys.path.insert(0, str(a.team / "src"))
    from dcc_data.mission2_features import is_seoul_path

    root = a.root
    pairs: dict[str, dict[str, str]] = {}
    for path in sorted((root / "Training").rglob("*")):
        if path.suffix.lower() in (".wav", ".json") and is_seoul_path(path.relative_to(root).as_posix()):
            group = pairs.setdefault(path.stem, {})
            if path.suffix.lower() in group:
                raise ValueError(f"duplicate source stem: {path.stem}")
            group[path.suffix.lower()] = path.relative_to(root).as_posix()
    stems = sorted(s for s, p in pairs.items() if len(p) == 2)
    print(f"paired Seoul Training calls: {len(stems)}")
    stems = random.Random(SEED).sample(stems, min(a.n_calls, len(stems)))
    rows = [dict(split="Training", stem=s, wav_path=pairs[s][".wav"], json_path=pairs[s][".json"]) for s in stems]

    a.out.mkdir(parents=True, exist_ok=True)
    local_tmp = Path(os.environ.get("TEMP", "/tmp")) / "m2_ssl_training_sample.tar"
    with tarfile.open(local_tmp, "w") as tar:
        for row in rows:
            for key in ("wav_path", "json_path"):
                tar.add(root / row[key], arcname=row[key], recursive=False)
    print(f"tar built: {local_tmp.stat().st_size / 1e9:.2f} GB")
    final = a.out / "training_sample.tar"
    tmp = a.out / "training_sample.tar.tmp"
    with open(local_tmp, "rb") as src, open(tmp, "wb") as dst:
        while chunk := src.read(1 << 24):
            dst.write(chunk)
    os.replace(tmp, final)
    local_tmp.unlink()
    (a.out / "sample.json.tmp").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(a.out / "sample.json.tmp", a.out / "sample.json")    # written last: stage() keys off sample.json
    print(f"wrote {final} and sample.json ({len(rows)} calls)")


if __name__ == "__main__":
    main()
