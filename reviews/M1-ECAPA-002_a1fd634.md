# M1-ECAPA-002 검토 (PR #150, a1fd634)

1. Validation 누수: OK — Training TL_/TS_ zip만 사용 (xvec-001의 prepare_rows 재사용), 전처리 통계는 fold train에서만 StandardScaler로 추정
2. 분할 누수: OK — CV는 성별 층화 StratifiedKFold, 호출 1개 = 1행(call_id 중복 시 실패)이라 통화 단위. seed 42 holdout은 캐시 split과 대조
3. 입력 필드: OK — 신고자 구간 음성만 사용, 성별은 정답으로만
4. M2: 해당 없음
5. 외부 데이터·네트워크: OK — speechbrain/spkrec-ecapa-voxceleb 고정 revision을 `$DCC_RUN_ROOT/models`에 받고 로컬 로드
9. requirements.txt: `speechbrain==1.0.3` 신규 1줄뿐 — 허용
6. 실행 계약: 2천 통화 청크 재개, fold×헤드 단계 파일 재개, metrics.json·best.ckpt 작성은 OK
7. 명세 일치: 헤드 c/h/i/j, 창 규칙, 5-fold(2026), McNemar, 판정 기준 구현은 OK
8. 버그: 아래 MAJOR

- [MAJOR] scripts/lab/m1-ecapa-002.py `load_baseline`(required 목록에 `stems`)와 `main`의 `cached['stems'].tolist() != [r.stem ...]` 비교 — M1-XVEC-002가 실제로 쓴 캐시 청크(spec commit bb9921b의 m1-xvec-002.py)는 acoustic·window_xvectors·window_lengths·durations·window_counts·xvector_seconds만 저장하고 `stems`가 없다(해당 파일에 `stems` 0건). 따라서 `Cache requires [...]` ValueError로 시작 직후 실패하고, 이 실험은 어떤 조건에서도 실행되지 않는다 — 고칠 방법: `stems`를 required에서 빼고 `data` 병합·`len(set(stems))` 검사·`stems_sha256`에서 제거. 행 순서 검증은 이미 있는 `digest != split['rows_sha256']`(xvec-002의 같은 정의)와 train/holdout 대조로 하고, 청크 파일명의 오프셋 연속성으로 행 수를 확인. `identity`의 `stems_sha256`은 `prepare_rows` 결과의 stems로 계산. ECAPA 청크 자체의 `stems` 저장·검사(자기 청크)는 유지해도 됨
- [MINOR] `window_bounds`의 첫 창 처리·`average_windows`는 캐시 규칙과 동등하나 zero-length 신고자 구간은 예외로 처리됨(xvec-002는 zero-pad). 29,200통화에서 0.5초 미만 케이스가 있으면 같은 이유로 실패하므로 스모크 확인 권장

VERDICT: FAIL
