변경 파일: `scripts/lab/m3-kcbert-011.py` — KCBERT-005 설정과 재개 기능을 유지하고, 두 순전파의 평균 가중 BCE + 대칭 Bernoulli KL을 구현했습니다.

import와 smoke 통과. PyTorch 미설치로 텐서 검증은 생략했으며, 학습·커밋·push는 실행하지 않았습니다.

COMMAND: python scripts/lab/m3-kcbert-011.py --out "$LAB_OUT"