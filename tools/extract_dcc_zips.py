"""INFRA job (runs on the Colab runner): extract the official data zip parts into the account's own Drive.

The shared '대학부 데이터' folder (teammate copy) holds only Google-Drive split zips
('대학부 데이터-<ts>-1-001.zip' ...). This copies them to local disk, extracts them (parts merge into one tree),
verifies counts, then copies the tree to /content/drive/MyDrive/<DEST>/ so the runner can find Training/ and
Validation/ (lab_runner.find_data_root accepts folders whose NFC name starts with '대학부 데이터').
Resumable by marker files in LAB_OUT. Writes LAB_OUT/metrics.json.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import unicodedata
import zipfile
from pathlib import Path

DRIVE = Path("/content/drive/MyDrive")
DEST = DRIVE / "대학부 데이터 압축해제"
LOCAL = Path("/content/dcc_extract")
OUT = Path(os.environ["LAB_OUT"])
NAME = "대학부 데이터"


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def find_zips() -> list[Path]:
    for _ in range(12):
        for d in DRIVE.iterdir():
            if nfc(d.name).startswith(NAME) and d.is_dir():
                zips = sorted(p for p in d.iterdir() if p.suffix.lower() == ".zip")
                if zips:
                    return zips
        time.sleep(10)
    raise SystemExit("zip 파트를 찾지 못함 (MyDrive의 '대학부 데이터' 바로가기 확인)")


def count(root: Path) -> dict:
    res = {}
    for split in ("Training", "Validation"):
        base = root / split
        res[split] = {"wav": sum(1 for _ in base.rglob("*.wav")), "json": sum(1 for _ in base.rglob("*.json"))} \
            if base.is_dir() else None
    return res


def main() -> None:
    t0 = time.time()
    LOCAL.mkdir(parents=True, exist_ok=True)
    zips = find_zips()
    print(f"zip parts: {len(zips)} ({sum(z.stat().st_size for z in zips) / 1e9:.1f} GB)", flush=True)
    ex = LOCAL / "x"
    for z in zips:
        mark = LOCAL / f"{z.name}.done"
        if mark.exists():
            continue
        local_zip = LOCAL / z.name
        shutil.copyfile(z, local_zip)                    # big sequential copy from Drive is fast
        with zipfile.ZipFile(local_zip) as zf:
            zf.extractall(ex)
        local_zip.unlink()
        mark.touch()
        print(f"extracted {z.name}", flush=True)
    roots = [p for p in ex.iterdir() if nfc(p.name) == NAME and (p / "Training").is_dir()]
    if not roots:
        raise SystemExit(f"압축 해제 결과에 '{NAME}/Training' 없음: {[p.name for p in ex.iterdir()]}")
    root = roots[0]
    local_counts = count(root)
    print("local counts:", local_counts, flush=True)

    target = DEST / NAME
    if not (OUT / "copied.done").exists():
        DEST.mkdir(parents=True, exist_ok=True)
        # rsync-like copy; reruns skip files already present with the same size
        subprocess.run(["cp", "-rn", str(root), str(DEST) + "/"], check=True)
    drive_counts = count(target)
    ok = drive_counts == local_counts
    if ok:
        (OUT / "copied.done").write_text(time.strftime("%F %T"))   # only a verified copy is skipped on rerun
    m = {"exp_id": os.environ.get("LAB_EXP_ID"), "seed": 0,
         "primary_metric": {"name": "copy_complete", "value": 1.0 if ok else 0.0, "split": "internal_holdout"},
         "metrics": {"zip_parts": len(zips), "local": local_counts, "drive": drive_counts, "dest": str(target),
                     "minutes": round((time.time() - t0) / 60, 1)}}
    (OUT / "metrics.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    print(m, flush=True)
    if not ok:
        raise SystemExit("Drive 복사본 개수가 로컬과 다름 (재실행하면 이어서 복사)")


if __name__ == "__main__":
    main()
