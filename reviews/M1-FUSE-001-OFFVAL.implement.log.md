- `scripts/lab/m1-fuse-001-offval.py`: 고정 FUSE 평가, 특징 캐시 재개·재사용, CSV·진단 지표 저장 구현.
- `requirements.txt`: `speechbrain==1.0.3` 추가.

10초 이내 smoke·import 확인 통과. 학습·실제 평가는 실행하지 않았습니다. ECAPA 원본 스크립트가 없어 FUSE에 기록된 추출 규칙으로 구현했습니다.

COMMAND: python scripts/lab/m1-fuse-001-offval.py --out "$LAB_OUT"