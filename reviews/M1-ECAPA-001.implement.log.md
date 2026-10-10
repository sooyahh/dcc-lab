- `scripts/lab/m1-ecapa-001.py`: ECAPA 특징·청크 재개, 기준 특징 검증·재사용, 4종 LR 비교와 지정 산출물 저장 구현.
- `requirements.txt`: `speechbrain==1.0.3`만 추가.

10초 이내 smoke와 스크립트 import 통과. 학습은 실행하지 않았으며, 의존성 미설치로 실제 모델 로드는 미검증입니다.

COMMAND: python scripts/lab/m1-ecapa-001.py --out "$LAB_OUT"