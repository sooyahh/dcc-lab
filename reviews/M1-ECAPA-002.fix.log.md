변경 파일: [scripts/lab/m1-ecapa-002.py](/home/runner/work/dcc-lab/dcc-lab/team/scripts/lab/m1-ecapa-002.py)

x-vector 캐시의 `stems` 의존성을 제거하고 manifest 해시·분할 검증을 유지했습니다. 0초 구간의 zero-pad·평균 처리도 수정했습니다.

Import·diff 검사 통과. Smoke는 환경의 `numpy` 부재로 검증하지 못했습니다. 학습·커밋·push·PR은 실행하지 않았습니다.

COMMAND: python scripts/lab/m1-ecapa-002.py --out "$LAB_OUT"