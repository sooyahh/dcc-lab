변경 파일: [scripts/lab/m3-roberta-004.py](scripts/lab/m3-roberta-004.py)

Training 전용 보조 라벨 선정, 멀티태스크 손실, 재개 체크포인트, 평가 지표·확률 저장과 export 호환 체크포인트를 구현했습니다. import와 smoke 통과. torch 미설치로 텐서 검증은 생략했으며 학습은 실행하지 않았습니다.

COMMAND: python scripts/lab/m3-roberta-004.py --out "$LAB_OUT"