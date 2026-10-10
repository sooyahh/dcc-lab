- 추가 파일: `scripts/lab/m3-roberta-005.py`
- 보조 weighted BCE + soft-F1, 재개 체크포인트, epoch별 진단·평가·확률 저장 구현.
- smoke·import 통과. torch 미설치로 텐서 검사는 생략했으며 학습은 실행하지 않았습니다.
- 004 원본이 없어 보조 20개 목록·헤드의 정확한 동일성은 미확인입니다.

COMMAND: python scripts/lab/m3-roberta-005.py --out "$LAB_OUT"