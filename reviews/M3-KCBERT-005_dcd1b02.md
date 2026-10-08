# M3-KCBERT-005 검토 (PR #76, dcd1b02)

m3-kcbert-003.py(검토 PASS)와 diff 비교: 변경은 EXP_ID, docstring, weight 공식(0.25/3.0 → 0.5/6.0), smoke 단언, notes뿐이다.

1. Validation 누수: OK — Training/TL_서울_구급.zip만 읽음, pos_weight는 train 분할 라벨로만 계산 (공식 Val 미사용, 명세 uses_official_val=false 일치)
2. 분할 누수: OK — call_id 중복 시 중단, train/holdout call_id 교집합 검사 (prepare_split)
3. 입력 화이트리스트: OK — 전사 text만 특징, 라벨은 타깃으로만 사용
4. M2 발화 독립성: 해당 없음 (M3)
5. 외부 데이터/네트워크/비밀: OK — 고정 revision 공개 모델만 DCC_RUN_ROOT/models에 다운로드, 비밀 접근 없음
9. requirements.txt: OK — 변경 없음
6. 실행 계약: OK — metrics.json 작성, seed별 결과·ckpt_last.pt 재개, atomic write
7. 명세 일치: OK — pos_weight만 변경, command가 스크립트 인자(--out)와 일치
8. 명백한 버그: 없음 — seed 고정, 셔플(generator), threshold >0.5 고정

VERDICT: PASS
