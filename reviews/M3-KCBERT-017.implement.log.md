변경 파일: [scripts/lab/m3-kcbert-017.py](/home/runner/work/dcc-lab/dcc-lab/team/scripts/lab/m3-kcbert-017.py)

KCBERT-012에 보조 헤드·손실, 15분 단위 재개, 안전한 체크포인트 저장과 seed별 진단 지표를 추가했습니다.

import·smoke 통과. torch 미설치로 tensor 검사는 생략했습니다. ROBERTA-005 참조가 없어 보조 라벨은 Training 빈도로 선정하며, 정확히 20개가 아니면 중단합니다.

COMMAND: python scripts/lab/m3-kcbert-017.py --out "$LAB_OUT"