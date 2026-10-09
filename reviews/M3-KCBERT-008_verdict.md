VERDICT: 재시도
- 실행 0.7분 만에 종료(exit 1), metrics.json 없음 — 학습 전 코드 오류이며 실험 결과가 아님.
- 원인: scripts/lab/m3-kcbert-008.py:167 `tokenizer.prepare_for_model`이 현재 Colab transformers(BertTokenizer 래퍼)에 없음 (AttributeError). 004의 `build_inputs_with_special_tokens`와 같은 유형.
- 동일 커밋 2f96203 재제출은 같은 오류로 실패하므로 제출하지 않음. PR #84에 수정 요청(lab-fix) — 특수토큰을 직접 `[cls_token_id] + 윈도우 내용 + [sep_token_id]`로 구성하고 패딩·마스크도 직접 처리, tokenizer 래퍼 전용 메서드 사용 금지.
- 수정 PR 재검토 PASS 후 재제출 (재시도 1회, 시도 1/3 소진).
- 판정 대상 성능 지표 없음 (baseline KCBERT-005 0.6092 비교 불가).
