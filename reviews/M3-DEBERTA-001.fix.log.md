변경 파일: `scripts/lab/m3-deberta-001.py`

로컬 `tokenizer.json` 직접 로딩 폴백과 모델 로드 전 한국어 토큰화 검사를 추가했습니다. import·smoke 통과. 실제 모델 검증은 환경 제약으로 수행하지 않았으며, 학습·커밋·push는 하지 않았습니다.

COMMAND: python scripts/lab/m3-deberta-001.py --out "$LAB_OUT"