- `scripts/lab/m3-qwen-001.py`: Qwen LoRA 학습, epoch별 재개·지표 저장, holdout 확률 저장, fp16 병합 모델 내보내기 구현.
- `requirements.txt`: 새 의존성 `peft==0.13.2` 추가.

import·smoke 통과. 현재 환경에 torch가 없어 텐서 검증은 생략했습니다. 학습·커밋·push는 실행하지 않았습니다.

COMMAND: python scripts/lab/m3-qwen-001.py --out "$LAB_OUT"