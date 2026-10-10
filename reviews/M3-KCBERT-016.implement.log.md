변경 파일: [scripts/lab/m3-kcbert-016.py](scripts/lab/m3-kcbert-016.py)

λ=0.1·0.3의 3-seed 학습, λ=0·1 체크포인트 재평가, 재개 처리와 F1·ECE·Brier 비교표 저장을 구현했습니다.

import·기본 smoke·문법 검사를 통과했습니다. torch·numpy 부재로 수치 검사는 생략했고, 학습·커밋·push는 실행하지 않았습니다.

COMMAND: python scripts/lab/m3-kcbert-016.py --out "$LAB_OUT"