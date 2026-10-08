변경 파일: `scripts/lab/m3-kcbert-003.py`

완화 가중 BCE, 3개 seed, 캐시·체크포인트 재개, metrics 저장을 구현했습니다. import·smoke 검증 통과, 학습은 실행하지 않았습니다.

KCBERT-002가 없어 P1 v5를 참고했으며, 기준 실험과의 동일성은 미확인입니다. 의존성 변경은 없습니다.

COMMAND: python scripts/lab/m3-kcbert-003.py --out "$LAB_OUT"