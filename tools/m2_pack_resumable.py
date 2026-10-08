"""Resumable, faster drop-in for the team repo's scripts/pack_mission2_spectrograms.py (commit 4bfd2c4).

Same output: identical sort (call_id, utt_idx), frame_offset, float16 (n_frames, n_mels) rows, same .npy
format (np.lib.format.open_memmap) and the same packed index parquet. Differences are operational only:
  * progress is checkpointed to <packed>.tmp.npy.progress every CHECKPOINT rows (after flushing the memmap),
    so a killed run continues where it stopped instead of starting over;
  * files are read by a thread pool (np.load is I/O bound on ~890k small files).

    python tools/m2_pack_resumable.py --index IDX --spectrogram-dir DIR --packed-output OUT --index-output IDX_OUT
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

PACKED_DTYPE = np.float16
CHECKPOINT = 20_000
BATCH = 2_000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--spectrogram-dir", type=Path, required=True)
    ap.add_argument("--packed-output", type=Path, required=True)
    ap.add_argument("--index-output", type=Path, required=True)
    ap.add_argument("--threads", type=int, default=8)
    a = ap.parse_args()
    t0 = time.monotonic()
    if sys.platform == "win32":                              # block idle sleep while this process runs (no settings change)
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED

    index_df = pd.read_parquet(a.index)
    if "frame_offset" in index_df.columns:
        raise ValueError("index already has a frame_offset column -- it is already a packed index")
    n_mels_values = index_df["n_mels"].unique()
    if len(n_mels_values) != 1:
        raise ValueError(f"index mixes several n_mels values: {sorted(n_mels_values)}")
    n_mels = int(n_mels_values[0])
    packed_df = index_df.sort_values(["call_id", "utt_idx"], kind="stable").reset_index(drop=True)
    n_frames = packed_df["n_frames"].to_numpy(dtype=np.int64)
    offsets = np.concatenate([[0], np.cumsum(n_frames)[:-1]]).astype(np.int64)
    packed_df["frame_offset"] = offsets
    paths = packed_df["npy_path"].tolist()
    total = len(paths)
    shape = (int(n_frames.sum()), n_mels)

    tmp = a.packed_output.with_name(a.packed_output.name + ".tmp.npy")
    progress = tmp.with_name(tmp.name + ".progress")
    start = 0
    if tmp.exists() and progress.exists():
        start = int(progress.read_text().strip())
        packed = np.lib.format.open_memmap(tmp, mode="r+")
        if packed.shape != shape or packed.dtype != PACKED_DTYPE:
            raise ValueError(f"existing {tmp} has shape {packed.shape}/{packed.dtype}, expected {shape}")
        print(f"  resume from {start}/{total}", flush=True)
    else:
        tmp.unlink(missing_ok=True)
        packed = np.lib.format.open_memmap(tmp, mode="w+", dtype=PACKED_DTYPE, shape=shape)
        progress.write_text("0")

    def load(i: int) -> np.ndarray:
        spec = np.load(a.spectrogram_dir / paths[i])
        if spec.shape != (n_mels, n_frames[i]):
            raise ValueError(f"{paths[i]}: shape {spec.shape} does not match its index row "
                             f"(n_mels={n_mels}, n_frames={n_frames[i]})")
        return spec

    try:
        with ThreadPoolExecutor(max_workers=a.threads) as pool:
            i = start
            while i < total:
                batch = range(i, min(i + BATCH, total))
                for j, spec in zip(batch, pool.map(load, batch)):
                    packed[offsets[j]: offsets[j] + n_frames[j]] = spec.T
                i = batch.stop
                if i % CHECKPOINT == 0 or i == total:
                    packed.flush()
                    progress.write_text(str(i))
                    print(f"  packed {i}/{total} ({time.monotonic() - t0:.0f}s)", flush=True)
        packed.flush()
    finally:
        del packed  # Windows can't rename a still-mapped file

    tmp.replace(a.packed_output)
    progress.unlink(missing_ok=True)
    a.index_output.parent.mkdir(parents=True, exist_ok=True)
    packed_df.to_parquet(a.index_output, index=False)
    print(f"Packed {total} spectrograms ({shape[0]} frames) -> {a.packed_output}")
    print(f"Packed index -> {a.index_output}")
    print(f"Elapsed: {time.monotonic() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
