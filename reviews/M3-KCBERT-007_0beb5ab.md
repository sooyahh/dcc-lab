# M3-KCBERT-007 검토 (0beb5ab)

1. Validation 누수: OK — 공식 Val 경로 없음(Training/TL_서울_구급.zip만 읽음), uses_official_val=false, official_val=null
2. 분할 누수: OK — split 후 call_id 교집합 검사(m3-kcbert-007.py prepare_split), call_id 중복 행이면 실패
3. 입력 필드: OK — utterances[].text만 사용, 라벨은 symptom만 타깃
4. M2 독립성: 해당 없음(M3)
5. 외부/네트워크: OK — 고정 revision으로 DCC_RUN_ROOT/models에 받고 이후 local_files_only, LAB_OUT/LAB_WORK만 쓰기
9. requirements.txt: 변경 없음. 참고: iterstrat는 목록에 없으나 005(채택·실행됨)와 동일 의존 [MINOR]
6. 실행 계약: OK — seed별 결과/ckpt_last 원자적 저장·복원(seed 불일치 시 건너뜀), metrics.json·best.ckpt 작성, 완료 시 재사용
7. 명세 일치: OK — 005 설정(256토큰, 가중 BCE 0.5/6, 3ep, seed 42/43/44) 동일, sigmoid 평균 후 >0.5 고정, 단일 seed 결과 함께 기록. command 인자 일치
8. 버그: 발견 없음 — micro F1 집계, 확률 정렬(holdout 일치) 검증, seed 고정/셔플 확인

BLOCKER·MAJOR 0건.

VERDICT: PASS
