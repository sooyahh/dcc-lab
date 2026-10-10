변경 파일: [scripts/lab/m3-roberta-006.py](/home/runner/work/dcc-lab/dcc-lab/team/scripts/lab/m3-roberta-006.py)

보조 확률을 연결하는 계층형 헤드, epoch 재개, 요청 지표 저장을 구현했습니다. import·smoke 통과했으며, torch 부재로 gradient 검사는 생략했습니다. 학습은 실행하지 않았습니다.

실행에는 005 보조 라벨 경로, P0 분할 경로·SHA256 환경 변수 설정이 필요합니다.

COMMAND: python scripts/lab/m3-roberta-006.py --out "$LAB_OUT" --aux-labels "$LAB_AUX_LABELS" --split "$LAB_P0_SPLIT" --split-sha256 "$LAB_P0_SPLIT_SHA256"