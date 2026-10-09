변경 파일: `scripts/lab/m3-roberta-003.py`

강화 BCE + fp32 soft-F1 손실, 3-seed 지표·epoch별 손실 기록, 체크포인트 재개를 구현했습니다. ROBERTA-002가 없어 ROBERTA-001 구조를 재사용했습니다.

import·smoke 통과. `torch` 부재로 텐서 검사는 생략했고, 학습은 실행하지 않았습니다.

COMMAND: python scripts/lab/m3-roberta-003.py --out "$LAB_OUT"