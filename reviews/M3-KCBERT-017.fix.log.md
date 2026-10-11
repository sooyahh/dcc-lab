변경 파일: [scripts/lab/m3-kcbert-017.py](/home/runner/work/dcc-lab/dcc-lab/team/scripts/lab/m3-kcbert-017.py)

holdout을 파일명순으로 정렬해 `holdout_probs.npy`와 `val_files.txt`의 행 순서를 일치시켰습니다. train 순서는 유지했습니다.

import·10초 이내 smoke 통과. torch 미설치로 tensor 검사는 생략했습니다. 학습·커밋·push는 수행하지 않았습니다.

COMMAND: python scripts/lab/m3-kcbert-017.py --out "$LAB_OUT"