# M1-FUSE-001-OFFVAL 검토 (PR #178, 032d9f9)

1. Validation 누수: OK. 공식 Val은 평가 전용. 동결 FUSE 파이프라인으로 `predict_proba`만 호출, fit 없음. 결합 0.5/0.5, 임계값 0.5 고정. `uses_official_val=true`와 일치.
2. 분할 누수: OK. 분할 없음, 3,640 call 전수 평가(`xv.prepare_rows`의 call_id 중복·3,640 검사 재사용).
3. 입력 화이트리스트: OK. 특징은 신고자 구간 음성(`extract_caller_segments`)에서만. gender는 예측·CSV 저장 후 채점용으로만 읽음(`_read_gender`).
4. M2 발화 독립성: 해당 없음(M1).
5. 외부 데이터·네트워크·비밀: OK. x-vector·ECAPA 모두 고정 revision을 `$DCC_RUN_ROOT/models`에 받고 로컬 로드, ECAPA는 `HF_HUB_OFFLINE=1`. 비밀 접근 없음. MINOR: sklearn `pip install --no-deps`는 XVEC-002-OFFVAL과 같은 명세 동작.
9. requirements.txt: MINOR. `speechbrain==1.0.3` 1줄 신규 추가(main에 없음, ECAPA-002 명세가 예고한 것과 동일, 명세 notes는 "이미 있으면 추가하지 않음"). 기존 패키지 변경 없음. 앞의 빈 줄은 무해.
6. 실행 계약: OK. metrics.json·best.ckpt(원본 복사)·predictions.csv 작성, 이미 완료 시 즉시 종료, x-vector·ECAPA 50통화 청크 원자 저장으로 재개, 두 모델 로드·ckpt 검증이 ZIP 복사 전에 실패. 이전 OFFVAL 캐시는 전 청크 검증 후에만 재사용, 불일치 시 재추출.
7. 명세 일치: OK. 원본 `m1-ecapa-002.py`(7fe2d84)와 대조: `encode_batch` 기본(normalize=False) → 창별 L2 → 길이 가중 평균(샘플 수 가중 = 초 가중과 동치) → L2, 창 규칙·0.5초 zero-pad 동일. 52D+512D / 52D+192D 입력 순서가 `average_windows` 기반 학습 특징과 같음. XVEC/ECAPA 창 수·길이 일치 검사 있음. 성공 기준 3,583건 = 0.98434 사전 고정과 일치. `--smoke` 통과.
8. 명백한 버그: 없음. MINOR: ECAPA 로드가 `overrides` 대신 hyperparams.yaml 재작성 방식(원본과 다름). 실패하면 ZIP 복사 전에 즉시 실패하므로 시간 낭비 작음.

BLOCKER·MAJOR 없음.

VERDICT: PASS
