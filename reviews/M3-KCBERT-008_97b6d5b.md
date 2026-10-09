# M3-KCBERT-008 검토 (PR #84, 97b6d5b)

1. Validation 누수: OK — `Training/TL_서울_구급.zip`만 읽음, 공식 Val 경로 없음 (`uses_official_val=false`와 일치)
2. 분할 누수: OK — 005와 동일 80:20 분할(prepare_split, 124~145줄), call_id 중복 행 거부 및 train/holdout call_id 교집합 검사. 청크는 call 내부에서만 생성
3. 입력 화이트리스트: OK — `utterances[].text`만 입력, 타깃은 `symptom`
4. M2 발화 독립성: 해당 없음 (M3)
5. 외부 데이터·네트워크·비밀: OK — kcbert-base 고정 revision(0f2f3f8)을 `$DCC_RUN_ROOT/models/`에 받고 `local_files_only=True`, main() 시작 직후 준비·로드 검증(381줄). 토큰·Drive 외부 수정 없음
9. requirements.txt: 변경 없음, OK
6. 실행 계약: OK — seed별 metrics/best.ckpt 건너뛰기(232~237줄), epoch마다 `ckpt_last.pt` atomic replace(모델·옵티마이저·scaler·RNG·history), 최종 `metrics.json` 작성, 경로는 find_data_root/LAB_WORK 사용
7. 명세 일치: OK — 256 윈도우(특수토큰 포함), stride 128, 최대 3청크, 청크 로짓 평균(학습·추론 동일), 가중 BCE, lr 2e-5, 3 epoch, thr 0.5, seed 42/43/44, 청크 분포 기록. COMMAND가 인자와 일치
8. 명백한 버그: 없음 — 윈도우 경계 산술 확인(0/128/256), 토크나이저 래퍼 호환(CLS/SEP/PAD 직접 구성), 비재진입 activation checkpoint(preserve_rng_state)와 autocast/GradScaler 조합 정상, 호출 단위 평균 로짓 후 BCE, 평가는 call 단위 sigmoid>0.5

[MINOR] scripts/lab/m3-kcbert-008.py:264 — ckpt_last.pt가 seed 간 공유되나 seed 불일치 시 새로 시작하고 완료 seed는 건너뛰므로 문제 없음

VERDICT: PASS
