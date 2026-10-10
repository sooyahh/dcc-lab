변경 파일:
- `scripts/lab/m3-xlmr-001.py`
- `lab_ops/specs/M3-XLMR-001.json`

고정 revision XLM-R, seed 42 학습·재개, holdout 확률/ID 및 지표 저장을 구현했습니다. import와 10초 이내 smoke 통과. torch 미설치로 텐서 검증은 생략했으며 학습은 실행하지 않았습니다.

COMMAND: python scripts/lab/m3-xlmr-001.py --out "$LAB_OUT"