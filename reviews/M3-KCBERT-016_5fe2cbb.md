# M3-KCBERT-016 검토 (PR #117, 5fe2cbb)

1. Validation 누수: OK. `Training/TL_서울_구급.zip`만 읽음. 공식 Val 경로 없음, `official_val=None`.
2. 분할 누수: OK. `prepare_split`이 call_id 교집합 검사. 005/012의 split.json(rows_sha256·train·holdout 집합)과 일치 여부를 재평가 전에 검증.
3. 입력 필드: OK. 전사 text만 사용, 라벨은 symptom만 타깃으로 사용.
4. M2 독립성: 해당 없음(M3).
5. 외부 데이터·네트워크: OK. 고정 revision(0f2f3f8)으로 `$DCC_RUN_ROOT/models/`에 받고 이후 `local_files_only=True`. 비밀 접근 없음. 쓰기는 LAB_OUT/LAB_WORK 한정.
9. requirements.txt: 변경 없음.
6. 실행 계약: OK. metrics.json 작성, 완료 seed 건너뛰기, `ckpt_last.pt` 원자적 교체·RNG 복원. 공유 ckpt_last는 seed·λ 불일치 시 무시하고 새로 시작(문제 없음). 예상 소요: 012가 3 seed 55.6분 → 새 학습 6회 약 2시간 + 추론, 예산 3시간 이내.
7. 명세 일치: OK. λ=0.1·0.3 고정, 3 seed 학습. λ=0(005)·λ=1(012)은 ckpt 추론만(config 키·soft_f1_weight 기본값 0/1.0 호환 확인, 없으면 skipped 기록). ECE(증상별 15구간 평균)·Brier·평균확률−양성비율·빈 예측 수·epoch별 F1·seed std 기록, holdout_probs.npy(행 순서 = val_files.txt 정렬) 저장, 판정은 `>= 0.5` 고정·후처리 없음.
8. 명백한 버그: 발견 없음. 지표는 마지막 epoch 기준이고 epoch/threshold 선택 없음.

[심각도: MINOR] 대표 지표(`primary_metric`)가 λ=0.1 평균뿐이므로 판정은 comparison_table 전체로 해야 함.

VERDICT: PASS
