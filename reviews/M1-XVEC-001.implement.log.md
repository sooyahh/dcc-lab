변경 파일: `scripts/lab/m1-xvec-001.py`

Training 전용 3종 LR 비교, 특징 청크 재개, 고정 revision WavLM 로드, McNemar·성별 recall·처리량 기록을 구현했습니다. Smoke와 스크립트 import 확인이 통과했습니다. 의존성 부재로 실제 모델 로드는 미검증입니다.

LR은 epoch 재개 API가 없어 중단된 fit만 다시 실행하며, 완료한 헤드는 건너뜁니다.

COMMAND: python scripts/lab/m1-xvec-001.py --out "$LAB_OUT"