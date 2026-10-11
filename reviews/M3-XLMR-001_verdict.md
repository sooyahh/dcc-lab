VERDICT: 보류
- 실행 문제: 재시도(1회 허용분)까지 총 2차례 모두 종료됐고 metrics.json이 없다. 마지막 실행은 epoch 3 종료 후 `ckpt_last.pt` 저장 중 Drive 임시 파일이 사라져(FileNotFoundError, `atomic_write`) 중단됐다. 재시도 한도에 도달해 더 제출하지 않는다.
- 진행: seed 42 epoch 1 holdout Macro F1 0.6237, epoch 2 0.6342(빈 예측 254건, ECE 0.042, Brier 0.082). epoch 3 학습은 끝까지 진행(loss 정상)했으나 holdout 평가·holdout_probs 저장 전에 중단됐다.
- 기준 비교: ROBERTA-003 0.6441, 성공 기준 0.6541. epoch 2까지 0.6342로 미달 추세이고 학습 붕괴는 없다.
- 미완료 결과(3 epoch 평가·holdout_probs 없음)라 채택·기각 근거로 쓰지 않는다. E5-001도 같은 양상이라 large 인코더 교체 계열은 우선순위를 낮춘다.
- 필요하면 사용자가 재제출을 결정한다(Drive 쓰기 오류가 원인이라 코드 수정 불필요, ckpt_last 이어 가기). 코드 PR #144는 열어 둔다.
