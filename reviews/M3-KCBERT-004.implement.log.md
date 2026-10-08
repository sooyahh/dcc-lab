변경 파일: [scripts/lab/m3-kcbert-004.py](/home/runner/work/dcc-lab/dcc-lab/team/scripts/lab/m3-kcbert-004.py)

KCBERT-003을 재사용해 입력만 앞 127 + 뒤 127 + 특수토큰 2개로 변경했습니다. 분할·손실·재개 로직은 유지했습니다. smoke와 import 확인 통과, 학습·커밋·push는 실행하지 않았습니다.

COMMAND: python scripts/lab/m3-kcbert-004.py --out "$LAB_OUT"