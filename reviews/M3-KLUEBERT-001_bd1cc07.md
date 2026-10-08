# M3-KLUEBERT-001 검토 (PR #82, bd1cc07)

KCBERT-005(통과·채택·병합된 코드)와 diff: 인코더/리비전/모델 캐시 경로, token_type_ids 전달만 변경.

1. Validation 누수: OK — `Training/TL_서울_구급.zip`만 읽음, 공식 Val 미사용 (명세 false 일치)
2. 분할 누수: OK — call_id 중복 시 예외, train/holdout call_id 교집합 검사 (prepare_split)
3. 입력 화이트리스트: OK — utterances[].text만 사용
4. M2 독립성: 해당 없음 (M3)
5. 외부 데이터·네트워크: OK — 고정 revision(77c8b3d, 005와 같은 짧은 해시 방식)으로 `$DCC_RUN_ROOT/models`에 받고 local_files_only 로드, main() 초반에 모델 로드 확인
9. requirements.txt: OK — 변경 없음
6. 실행 계약: OK — epoch마다 ckpt_last.pt를 atomic 교체, seed별 완료 산출물 건너뛰기, metrics.json·best.ckpt 작성
7. 명세 일치: OK — 인코더만 교체, 하이퍼파라미터·pos_weight·seed 동일, COMMAND가 인자와 일치
8. 명백한 버그: OK — token_type_ids를 학습·평가 모두 전달, threshold >0.5 고정, seed 고정
[MINOR] m3-kluebert-001.py:30 — 짧은 해시 revision — 005와 동일 방식이라 유지, 실패해도 데이터 준비 전에 즉시 실패

VERDICT: PASS
