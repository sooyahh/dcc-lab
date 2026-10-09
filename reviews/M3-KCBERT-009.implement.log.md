변경 파일: [scripts/lab/m3-kcbert-009.py](/home/runner/work/dcc-lab/dcc-lab/team/scripts/lab/m3-kcbert-009.py)

005의 학습·분할·재개 설정을 유지하고 CLS를 마스크 평균 풀링으로 교체했습니다. import와 10초 이내 smoke 통과. 현재 환경에 torch가 없어 풀링은 경량 텐서 fixture로 검증했습니다. 학습·커밋·push는 하지 않았습니다.

COMMAND: python scripts/lab/m3-kcbert-009.py --out "$LAB_OUT"