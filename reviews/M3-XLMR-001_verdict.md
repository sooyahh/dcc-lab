VERDICT: 재시도
- 실행 문제: attempt 3회 모두 러너 중단(max_attempts 초과)으로 종료됐고, metrics.json이 없다(결과 아님).
- 진행: seed 42 epoch 1 holdout Macro F1 0.6237, epoch 2 0.6342(빈 예측 254건, ECE 0.042, Brier 0.082, 학습 붕괴 없음). epoch 3 step 1200 부근에서 중단. epoch당 약 27분.
- 코드 오류·OOM 징후는 없다(리뷰 PASS, loss 정상 감소). ckpt_last에서 이어 가므로 남은 epoch만 필요하다.
- 같은 실험의 첫 재시도이므로 명세 변경 없이 `--force`로 재제출한다(예산 3h로 충분).
- 가설(ROBERTA-003 0.6441 대비 +0.01)은 아직 미판정이다. epoch 2까지는 기준 미달 추세.
