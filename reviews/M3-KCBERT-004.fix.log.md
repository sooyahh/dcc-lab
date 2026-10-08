변경 파일: [scripts/lab/m3-kcbert-004.py](/home/runner/work/dcc-lab/dcc-lab/team/scripts/lab/m3-kcbert-004.py)

특수토큰을 `[cls_token_id] + 앞127·뒤127 내용 + [sep_token_id]`로 직접 구성하도록 수정했습니다. 래퍼 호환성·패딩·마스크 smoke, import, diff 검사 통과. 학습·커밋·push는 실행하지 않았습니다.

COMMAND: python scripts/lab/m3-kcbert-004.py --out "$LAB_OUT"