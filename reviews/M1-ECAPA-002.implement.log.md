변경 파일:

- `scripts/lab/m1-ecapa-002.py`: ECAPA 추출, 캐시 검증·재개, 고정 5-fold CV·holdout 평가, 최종 모델 저장 구현.
- `requirements.txt`: `speechbrain==1.0.3` 추가.

Smoke·import·diff 검사 통과. 학습과 커밋·push·PR은 실행하지 않았습니다.

COMMAND: python scripts/lab/m1-ecapa-002.py --out "$LAB_OUT"