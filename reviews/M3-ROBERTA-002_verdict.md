VERDICT: 재시도
- 실행 문제(budget_hours 5h 초과, 301분)로 중단. 모델 결과 문제가 아님. seed 42(0.6271)·seed 43(0.6218)은 epoch 3까지 완료, seed 44는 epoch 3 step 1400 직전(epoch 2 Macro F1 0.6218)에서 중단.
- 학습 붕괴 없음. 다만 오심 재현율은 seed 44 epoch 2에서 0.21로 여전히 낮아 가중 BCE 효과는 최종 3-seed 평균으로 확인해야 함.
- 명세 조정: budget_hours 5→6. 완료 seed와 ckpt_last 이어가기로 잔여 약 1 epoch + 평가만 필요. 재시도 1회(코드·commit 동일, 검토 PASS 유효).
