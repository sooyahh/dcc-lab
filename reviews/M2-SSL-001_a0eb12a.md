# M2-SSL-001 검토 (PR #66, a0eb12a)

이전 검토(df5cb39) FAIL 사유 재확인:
- MAJOR(모델 가중치 경로) 해결 — `prepare_model()`이 `main()` 시작 직후(stage 이전) 고정 revision `4c66d48…`(HF API로 실재 확인, pytorch_model.bin·config·preprocessor 존재)을 `$DCC_RUN_ROOT/models/wavlm-base-plus`(Drive 영구 경로)에 받고 snapshot.json으로 identity 검증, 이후 `local_files_only=True`. `--model-dir`이 LAB_WORK 하위면 거부 (m2_ssl_001.py:40-59, 376-382)
- MINOR(패딩) 해결 — batch_size 1 고정 (:363)
- MINOR(memmap) 해결 — memmap은 LAB_WORK, 100통화마다 LAB_OUT으로 복사 후 `extraction.json` 갱신 (:62-71, :184-248)
- requirements.txt 변경 없음 (diff 0)

1. Validation 누수: OK — `root/'Training'`만 순회 + `is_seoul_path` (:130-131), `official_val=None`
2. 분할 누수: OK — GroupShuffleSplit call_id, 교집합 assert (:269-270)
3. 입력 필드: OK — startAt/endAt/speaker만 (build_utterance_records)
4. M2 발화 독립성: OK — 발화 구간만 crop/pooling, L1도 발화 단독, 스케일러는 train 행만
5. 외부·비밀: OK — 공개 모델 고정 revision 다운로드만(허용), 토큰·환경변수 접근 없음, 쓰기는 LAB_OUT/LAB_WORK/모델 폴더
6. 실행 계약: OK — 추출은 100통화 단위 원자적 커밋 후 재개, 헤드는 ckpt_last.pt(RNG 포함)에서 재개, metrics.json·best.ckpt 작성
7. 명세 일치: OK — 4/8/12층 mean+std, LR/LGBM, 동일 분할 L1 LGBM, 처리량·seed 기록. COMMAND의 인자(--out, --model-dir)가 스크립트와 일치
8. 명백한 버그: 없음 (라벨 0/1 int, hidden_states 인덱스 정상, seed 고정)

## 문제
[심각도: MINOR] :273-317 — 승자 층·헤드를 평가에 쓰는 같은 holdout으로 선택 → +2%p 판단에 약한 낙관 편향(코드 notes에 명시됨). 판정 시 감안.
[심각도: MINOR] :246 — 100통화마다 ~1.1GB Drive 복사(총 40회). 느리지만 재개 안전성 우선으로 허용.

[심각도: MINOR] PR 본문 `COMMAND:`의 `--model-dir "$LAB_WORK/models/wavlm-base-plus"`는 코드가 거부(:380-381)하므로 제출 명령에서는 `--model-dir`을 생략(기본값 `$DCC_RUN_ROOT/models/wavlm-base-plus`).

VERDICT: PASS
