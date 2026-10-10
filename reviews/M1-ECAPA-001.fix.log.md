- `scripts/lab/m1-ecapa-001.py`: 모델을 `LAB_WORK`로 원자적 복사 후 로드하고, `LocalStrategy.COPY`와 내부 torchaudio shim 적용.

10초 이내 smoke·스크립트 import·diff 검사 통과. 학습은 실행하지 않았습니다. 모델 의존성이 없어 실제 로드는 미검증입니다.

COMMAND: python scripts/lab/m1-ecapa-001.py --out "$LAB_OUT"