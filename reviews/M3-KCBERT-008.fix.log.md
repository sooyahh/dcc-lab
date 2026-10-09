변경 파일: [scripts/lab/m3-kcbert-008.py](/home/runner/work/dcc-lab/dcc-lab/team/scripts/lab/m3-kcbert-008.py)

래퍼 전용 메서드를 제거하고 CLS·SEP 토큰, 패딩·마스크를 직접 구성하도록 수정했습니다. 경계 길이별 smoke, import, diff 검사 통과. 학습은 실행하지 않았습니다.

COMMAND: python scripts/lab/m3-kcbert-008.py --out "$LAB_OUT"