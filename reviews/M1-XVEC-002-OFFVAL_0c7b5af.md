# M1-XVEC-002-OFFVAL 검토 (PR #137, 0c7b5af)

1. Validation 누수: OK. 공식 Val은 평가 전용. `joblib.load`한 동결 파이프라인으로 `predict`만 하고 fit/partial_fit 없음(scripts/lab/m1-xvec-002-offval.py main). `uses_official_val=true`와 일치.
2. 분할 누수: OK. 분할 없음, 3,640 call 전수 평가·call_id 중복 검사(prepare_rows).
3. 입력 화이트리스트: OK. 특징은 신고자 구간 음성(`extract_caller_segments`, startAt/endAt/Speaker)에서만. `gender`는 예측 확정 후 채점용으로만 읽음. 라벨 JSON의 `call_id`는 식별자로만 사용.
4. M2 발화 독립성: 해당 없음(M1).
5. 외부 데이터·네트워크·비밀: OK. 모델은 고정 revision을 `$DCC_RUN_ROOT/models`에 받고 `local_files_only` 로드. 비밀 접근 없음. MINOR: `prepare_sklearn`이 LAB_WORK로 `pip install --no-deps scikit-learn==<학습 버전>`(명세 notes에 명시된 동작, 추론 경로 아님).
9. requirements.txt: 변경 없음.
6. 실행 계약: OK. metrics.json·best.ckpt(원본 복사, sha256 검증)·predictions.csv 작성, 50통화 청크 원자적 캐시로 재개, 완료 시 즉시 종료. 작은 파일은 LAB_WORK에서만 읽음(zip 2개 복사).
7. 명세 일치: OK. 창 분할(20초×최대 4, 마지막 창 3초 이상, 첫 창 항상 포함), 창별 L2 → 길이 가중 평균 → L2, 52D+512D 순서가 원본 m1-xvec-002.py(`window_ranges`, `average_windows`, `[a, mean]`)와 동일. 성공 기준 0.9777 사전 고정, 길이 구간·창 수 분포·McNemar·시간·해시 기록.
8. 명백한 버그: 없음. MINOR: 신고자 파형 길이 0이면 원본과 달리 ValueError(원본은 zero-pad 처리) — 실데이터에선 발생하지 않을 것으로 보이며 발생 시 즉시 실패해 시간 낭비는 없음.

BLOCKER·MAJOR 없음.

VERDICT: PASS
