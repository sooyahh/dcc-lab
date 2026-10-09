변경 파일: [scripts/lab/m3-kcbert-015.py](scripts/lab/m3-kcbert-015.py)

012 기반으로 epoch 2·3의 상위 10% BCE 샘플 제외와 제외 건수 기록을 추가했습니다. soft macro-F1과 재개 기능은 유지했습니다.

smoke·import 확인 통과. 현재 환경에 torch가 없어 텐서·그래디언트 검증은 건너뛰었습니다. 학습·커밋·push는 실행하지 않았습니다.

COMMAND: PYTHONPATH=src python scripts/lab/m3-kcbert-015.py --out "$LAB_OUT"