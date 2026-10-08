# M3-KCBERT-006 검토 (PR #78, 1bce6d5)

1. Validation 누수: OK — `TL_서울_구급.zip`(Training)만 읽음, 공식 Val 경로 없음. 명세 `uses_official_val=false`와 일치.
2. 분할 누수: OK — 80:20 multilabel stratified(seed 42), call_id 중복 시 예외, 교집합 검사(`prepare_split`).
3. 입력 화이트리스트: OK — 발화 `text`만 사용(`transcript`). 라벨 키는 타깃으로만 사용.
4. M2 발화 독립성: 해당 없음(M3).
5. 외부 데이터·네트워크: OK — 고정 revision(0f2f3f8) HF 모델을 `$DCC_RUN_ROOT/models/kcbert-base`에 받고 `local_files_only`. main() 초반 `prepare_model()`로 선검증. 비밀 접근 없음.
9. requirements.txt: 변경 없음.
6. 실행 계약: OK — metrics.json 작성, epoch마다 `ckpt_last.pt` 원자적 교체, seed 단위 완료 건너뛰기, 시드 전환 시 이전 seed ckpt 무시 후 초기화.
7. 명세 일치: OK — KCBERT-005(PR #76) 스크립트와 diff 결과 EPOCHS 3→5, 고정 문구 외 동일(가중치 scale 0.5/max 6, 입력 256, thr 0.5, seed 42/43/44). command 인자 일치. 최종 epoch 평가, best epoch 선택 없음.
8. 명백한 버그: 발견 없음. (PR 본문의 "005 없음"은 005 PR 미병합 때문이며 실제 코드는 005와 동일.)

[심각도: MINOR] — `--smoke`가 통과 가능한 항목은 표준 라이브러리 검사뿐 — 조치 불필요.

VERDICT: PASS
