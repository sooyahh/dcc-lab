변경 파일:

- `scripts/lab/m3-kcelectra-001.py`: seed 42 학습·재개, P0 분할, 확률·평가지표 저장 구현.
- `lab_ops/specs/M3-KCELECTRA-001.json`: 설정과 고정 revision 기록.

import·smoke·문법 검사를 통과했습니다. torch가 없어 텐서 검사는 생략했으며, 학습은 실행하지 않았습니다.

COMMAND: python scripts/lab/m3-kcelectra-001.py --out "$LAB_OUT"