#!/usr/bin/env bash
# M2 L2 Training spectrogram build on the local PC (CPU), replacing the Colab build that died 2026-10-06 13:17.
# Same code as the Validation build (team repo commit 4bfd2c4; build/pack/verify code identical to main).
# Output matches what notebooks/mission2_l2_retrain.ipynb expects in MyDrive/dcc_runs/m2_l2_spec/:
#   m2_spectrograms_packed.npy (+ .sha256), m2_spectrogram_index_packed.parquet,
#   m2_spectrogram_index_full.parquet, m2_spectrogram_index_full_provided_labels.parquet
# Resumable by stage: a stage whose output already exists is skipped.
set -uo pipefail
TEAM="/c/Users/sooyah/Desktop/아주대/dcc/01_prelim/dcc2026-prelim"
SRC_REPO="/c/Users/sooyah/Desktop/아주대/dcc/m2spec-4bfd2c4"     # detached worktree of the team repo
WORK="/c/dcc_m2spec"                                              # ~14 GB npy + 7 GB pack, local disk only
DRIVE="/g/내 드라이브/dcc_runs/m2_l2_spec"
STATUS="$DRIVE/STATUS.txt"
W=${W:-10}
st(){ echo "$(TZ=Asia/Seoul date '+%F %T KST') $*" | tee -a "$WORK/local_build.log" "$STATUS"; }
fail(){ st "FAILED(local): $*"; exit 1; }
mkdir -p "$WORK"

[ -d "$SRC_REPO" ] || git -C "$TEAM" worktree add --detach "$SRC_REPO" 4bfd2c4 || fail "worktree"
cd "$SRC_REPO" || fail "cd"
MAN="$TEAM/data/manifests/dcc_manifest_v1.csv"
DR="$TEAM/data/raw"
LABELS="$TEAM/data/raw_merged/Training/2.라벨링데이터/TL_서울_구급"
export PYTHONPATH="$(cygpath -w "$SRC_REPO/src")" PYTHONUTF8=1 TQDM_MININTERVAL=60
IDX="$WORK/m2_spectrogram_index_full.parquet"
IDX_L="$WORK/m2_spectrogram_index_full_provided_labels.parquet"
PACK="$WORK/m2_spectrograms_packed.npy"
PIDX="$WORK/m2_spectrogram_index_packed.parquet"

if [ ! -f "$IDX" ]; then
  st "LOCAL_TRAIN_BUILD_START host=$(hostname) workers=$W commit=4bfd2c4"
  python scripts/build_mission2_spectrograms.py --manifest "$MAN" --data-root "$DR" --split training --n-calls -1 \
    --seed 42 --workers "$W" --output-dir "$WORK/m2_spec_train" --index-output "$IDX" \
    --failures-log "$WORK/m2_spectrogram_build_failures.jsonl" > "$WORK/train_build.log" 2>&1 \
    || fail "train build: $(tail -c 400 "$WORK/train_build.log")"
  grep -q "Spectrograms saved" "$WORK/train_build.log" || fail "no 'Spectrograms saved'"
  st "TRAIN_BUILD_DONE $(grep -E 'Spectrograms saved|Failures|Elapsed' "$WORK/train_build.log" | tr '\n' ' ')"
fi

if [ ! -f "$IDX_L" ]; then
  python scripts/verify_mission2_raw_labels.py --index "$IDX" --label-root "$LABELS" --output "$IDX_L" \
    > "$WORK/train_verify.log" 2>&1 || fail "train verify: $(tail -c 400 "$WORK/train_verify.log")"
  st "TRAIN_VERIFY_DONE $(python -c "import pandas as pd;d=pd.read_parquet(r'$IDX_L');print(len(d),d.label_source.unique().tolist())")"
fi

if [ ! -f "$PACK" ]; then
  python scripts/pack_mission2_spectrograms.py --index "$IDX_L" --spectrogram-dir "$WORK/m2_spec_train" \
    --packed-output "$PACK" --index-output "$PIDX" > "$WORK/train_pack.log" 2>&1 \
    || fail "train pack: $(tail -c 400 "$WORK/train_pack.log")"
  st "TRAIN_PACK_DONE $(grep -E '^Packed' "$WORK/train_pack.log" | head -1)"
fi

TS=$(sha256sum "$PACK" | cut -d' ' -f1)
IS=$(sha256sum "$PIDX" | cut -d' ' -f1)
echo "$TS  m2_spectrograms_packed.npy" > "$WORK/m2_spectrograms_packed.npy.sha256"
echo "$IS  m2_spectrogram_index_packed.parquet" > "$WORK/m2_spectrogram_index_packed.parquet.sha256"
for f in m2_spectrogram_index_full.parquet m2_spectrogram_index_full_provided_labels.parquet \
         m2_spectrogram_index_packed.parquet m2_spectrogram_index_packed.parquet.sha256 \
         m2_spectrograms_packed.npy.sha256 m2_spectrogram_build_failures.jsonl train_build.log train_verify.log train_pack.log; do
  [ -f "$WORK/$f" ] && cp -f "$WORK/$f" "$DRIVE/$f"
done
st "UPLOADING m2_spectrograms_packed.npy ($(du -h "$PACK" | cut -f1)) to Drive"
cp -f "$PACK" "$DRIVE/m2_spectrograms_packed.npy" || fail "copy pack to Drive"
DS=$(sha256sum "$DRIVE/m2_spectrograms_packed.npy" | cut -d' ' -f1)
[ "$TS" = "$DS" ] || fail "Drive copy sha mismatch local=$TS drive=$DS"
st "ALL_DONE (local build, commit 4bfd2c4) train_pack sha256=$TS index_packed sha256=$IS"
