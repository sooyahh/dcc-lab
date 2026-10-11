변경 파일: `scripts/lab/m3-deberta-001.py`

명세대로 DeBERTa·bf16·seed 42 실험과 재개 가능한 체크포인트, holdout 확률, ECE/Brier 기록을 구현했습니다. import와 smoke 통과. 현재 환경에 torch가 없어 텐서 검증은 생략했으며, 학습·커밋·push는 수행하지 않았습니다.

COMMAND: python scripts/lab/m3-deberta-001.py --out "$LAB_OUT"