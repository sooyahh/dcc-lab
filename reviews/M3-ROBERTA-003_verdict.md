VERDICT: 재시도
- 1차 실행이 budget_hours 3h 초과로 중단(182분). 실험 결과 판정 불가가 아니라 실행 시간 문제이며, 완료 seed와 ckpt_last 이어가기로 재개 가능.
- 완료분: seed 42 최종 Macro F1 0.6441, seed 43 0.6404 (둘 다 baseline ROBERTA-002 0.6241 초과). seed 44는 epoch 1(0.6333)까지 끝나고 epoch 2 도중 중단.
- 학습 붕괴 없음. 빈 예측은 epoch가 갈수록 감소(seed 43: 198→174→162). 오심 F1은 0.35 수준.
- 3-seed 평균이 없어 채택·기각은 보류. 남은 작업은 seed 44의 epoch 2~3(약 50분)이므로 예산을 4h로 늘려 1회 재시도.
