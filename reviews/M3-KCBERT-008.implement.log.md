변경 파일: [scripts/lab/m3-kcbert-008.py](/home/runner/work/dcc-lab/dcc-lab/team/scripts/lab/m3-kcbert-008.py)

최대 3개 슬라이딩 청크의 로짓 평균, micro-batch 역전파, 재개 체크포인트 및 seed별 F1·청크 분포 기록을 구현했습니다.

Smoke와 import 통과. 학습은 실행하지 않았으며, 현재 환경에 torch가 없어 GPU 동작은 검증하지 못했습니다.

COMMAND: python scripts/lab/m3-kcbert-008.py --out "$LAB_OUT"