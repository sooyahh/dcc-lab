# M3-KCBERT-003 실행 전 검토 (PR #71, 59caa13)

1. Validation 누수: OK — `Training/TL_서울_구급.zip`만 읽음, 공식 Val 접근 없음 (`uses_official_val=false`)
2. 분할 누수: OK — P0와 동일하게 정렬된 파일 순서 + `MultilabelStratifiedShuffleSplit(test_size=.2, random_state=42)`(P0 `_make_split` 동일 호출). call_id 중복·교집합 검사(:105, :124)
3. 입력 필드: OK — utterances의 text만 특징, 라벨은 symptom만 타깃
4. M2 발화 독립성: 해당 없음
5. 외부 데이터·네트워크·비밀: OK — 고정 revision을 `$DCC_RUN_ROOT/models/kcbert-base`에 받고 `local_files_only=True`; `main()` 초기에 모델 준비·로드 확인
9. requirements.txt: 변경 없음
6. 실행 계약: OK — seed별 결과 건너뛰기, epoch마다 `ckpt_last.pt` 원자 저장·RNG 복원(다른 seed ckpt는 무시), `metrics.json`·`best.ckpt` 작성
7. 명세 일치: OK — 앞 256토큰, `clip(.25*sqrt(neg/pos),1,3)` pos_weight를 train 분할에서만 계산, thr 0.5, 3 epoch, seed 42/43/44, command 인자 일치
8. 명백한 버그: 없음 (seed 고정, 셔플 generator 사용, 마지막 epoch 점수 사용)

## 문제
[심각도: MINOR] :27 — REVISION이 7자 단축 해시(KCBERT-002와 동일, 현재 정상 해석) — 40자 권장
[심각도: MINOR] 헤더 주석이 KCBERT-002 부재(P1 v5 기준)라 적었으나 002 설정과 동일하게 구성됨 — 베이스라인 동일성은 판정 시 확인
[심각도: MINOR] seed별 ckpt(~1.3GB) Drive 저장 용량 부담

VERDICT: PASS
