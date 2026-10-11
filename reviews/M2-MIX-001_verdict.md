VERDICT: 보류
- 실행 5.4분 만에 `prepare()` → `make_split()`에서 `ValueError: invalid H split`로 종료(attempt 1, 커밋 0f2e70e, colab-b). 학습·평가 전이라 metrics 없음, GPU 소모 거의 없음.
- 원인(코드 결함 추정): 코드는 `lm` 키를 zip 파일 stem으로 만들고(m2-mix-001.py:171 부근) `M2-SSL-002/split.json`의 call ID가 그 집합의 부분집합인지 검사한다. 반면 M2-SSL-002는 통화 JSON의 `_id`(없으면 stem)를 call ID로 썼다. 두 ID 체계가 다르면 `set(split['H']) <= set(ids)`가 실패한다. 검토(PASS)의 MINOR 지적이 그대로 현실화됨. Drive의 split.json은 직접 확인하지 못해 확정은 아님.
- 실행 환경 문제(OOM·시간 초과)가 아니라 같은 명령 재실행은 동일하게 실패하므로 `재시도`(명세 수정 후 재제출)가 아님. 코드 수정이 필요해 PR #168에 `lab-fix`를 달아 다음 실행에서 Codex가 수정하게 함.
- 수정 방향: 분할 검증을 `_id` 기준으로 통일(또는 stem↔`_id` 매핑)하고, 기존 split.json 검증 실패 시 원인(ID 샘플·개수)을 메시지에 남긴다. 기대 효과 판정은 결과 없음 → 보류.
