변경 파일: `scripts/lab/m3-softf1-001.py`

4개 팔 비교, 동일 split·샘플 순서, 중간 재개, OOM 시 쌍별 micro-batch 4 재시작, 팔별 확률·지표 저장을 구현했습니다. 학습·커밋·push는 하지 않았습니다.

import·구문·부분 smoke 통과. `torch` 미설치로 CPU 손실·기울기 검증은 미실행이며 `--smoke`에 포함했습니다.

COMMAND: python scripts/lab/m3-softf1-001.py --out "$LAB_OUT"