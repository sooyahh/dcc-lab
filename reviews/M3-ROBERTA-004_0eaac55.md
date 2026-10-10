# M3-ROBERTA-004 검토 (0eaac55)

1. Validation 누수: OK — `TL_서울_구급.zip`(Training)만 읽음, 공식 Val 경로 없음 (`uses_official_val` false와 일치)
2. 분할 누수: OK — 003과 같은 MultilabelStratifiedShuffleSplit(seed 42), call_id 중복 행 거부(:117), train/holdout call_id 교집합 검사(:140)
3. 입력 화이트리스트: OK — 입력은 `utterances[].text`만(:63). `symptom`은 라벨·보조 목표로만 사용(2026-10-10 멘토 답변 범위). speaker·triage·disaster* 미사용
4. M2 발화 독립성: 해당 없음(M3)
5. 외부 데이터·네트워크: OK — HF 고정 revision 28d9112를 `$DCC_RUN_ROOT/models/roberta-large`에 받고 `local_files_only`로 로드, `main()` 초반에 모델 준비(:410). 비밀·Drive 외부 수정 없음
9. requirements.txt: OK — 변경 없음
6. 실행 계약: OK — epoch마다 `ckpt_last.pt` atomic 교체 및 모델·옵티마이저·스케줄러·scaler·RNG 복원, 완료 단계 건너뛰기, `metrics.json`·`best.ckpt` 작성, `seed_42/holdout_probs.npy`·`val_files.txt` 저장
7. 명세 일치: OK — 보조 라벨은 Training 분할에서만 집계해 80건 이상(:147), aux 헤드 Linear(hidden,K)·dropout 공유, 손실 = 003 손실 + 0.5×보조 BCE(pos_weight 없음), 보조 라벨 선정에 holdout 미사용. `best.ckpt`의 model에서 `aux_classifier.*`를 제외하고 `aux_head`·`aux_labels`로 분리(export 호환). 판정 `>=0.5`, 후처리 없음. ECE(15구간)·Brier·확률−양성비율·빈 예측·epoch별 지표 기록. `command`가 스크립트 인자와 일치
8. 명백한 버그: 발견 없음 — 003과 같은 학습 루프(fp32 손실, 마이크로배치 가중 누적, scaler 스킵 시 스케줄러 유지), seed 고정, 셔플 generator 복원

- [심각도: MINOR] scripts/lab/m3-roberta-004.py:142 — `val_files.txt`가 003처럼 정렬되지 않고 holdout 인덱스 순서 — holdout_probs.npy와는 일치하므로 004 단독 사용에는 문제 없음. 003 확률과 행 단위로 합칠 때만 파일명으로 정렬해 맞출 것

VERDICT: PASS
