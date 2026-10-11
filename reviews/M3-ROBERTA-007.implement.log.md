변경 파일: `scripts/lab/m3-roberta-007.py`

512토큰·seed 42 실험, P0 분할 해시 검증, 15분 단위 재개, 안전한 체크포인트 복사와 요청 지표·확률 저장을 구현했습니다.

smoke/import 통과. torch 미설치로 텐서 검사는 생략했으며 학습은 실행하지 않았습니다.

COMMAND: python scripts/lab/m3-roberta-007.py --out "$LAB_OUT"