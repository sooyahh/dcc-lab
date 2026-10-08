# M2-SSL-001 검토 (PR #66, df5cb39)

1. Validation 누수: OK — `stage()`는 `root/'Training'`만 순회, `uses_official_val=false` 일치 (m2_ssl_001.py:94)
2. 분할 누수: OK — `GroupShuffleSplit` call_id 그룹, 교집합 assert (225-226)
3. 입력 필드: OK — `build_utterance_records`가 startAt/endAt/speaker만 읽음
4. M2 발화 독립성: OK — 발화 구간만 crop/pooling, L1도 context-free, StandardScaler는 train 행 통계만
5. 외부 데이터·비밀: 코드상 OK(`local_files_only=True`, 비밀 접근 없음). 단 모델 가중치 확보 경로가 없음 → 아래 MAJOR
6. 실행 계약: metrics.json·best.ckpt·ckpt_last 이어가기는 OK. 아래 MAJOR/MINOR 참고
7. 명세 일치: 4/8/12층, mean+std, LR/LGBM, 동일 분할 L1 LGBM, 처리량·seed 기록 OK
8. 명백한 버그: 없음

## 문제
[심각도: MAJOR] scripts/lab/m2_ssl_001.py:168-169, 304 — 기본/COMMAND의 `--model-dir "$LAB_WORK/models/wavlm-base-plus"`는 러너가 매 실험마다 새로 만드는 임시 로컬 디렉터리(`/content/lab_work/<EXP>`, runner/lab_runner.py:280-296)이고, 어떤 단계도 모델을 거기에 넣지 않는다(저장소 전체에 스테이징 코드 없음). `local_files_only=True`라 다운로드도 안 되므로 tar 스테이징과 utterance 색인(수십 분~수 시간) 이후 첫 모델 로드에서 반드시 실패한다 — 고칠 방법: (a) 사전에 Drive의 영구 경로(예: LAB_OUT 상위의 공유 models 폴더)에 가중치를 두고 COMMAND가 그 경로를 가리키게 하고, (b) `main()` 시작 직후(`stage()` 이전)에 `--model-dir/config.json` 존재를 검사해 즉시 실패시킨다. 가중치 반입 방식이 외부 다운로드라면 사용자 승인/규정 확인 필요.

[심각도: MINOR] :159 — LAB_OUT(Drive)에 1.1GB급 memmap 3개를 열어 두고 호출마다 `flush()`(4000회). Drive FUSE에서 mmap 쓰기는 느리거나 불안정할 수 있음 — LAB_WORK에 memmap을 두고 완료 시/주기적으로 LAB_OUT에 복사하면 안전.
[심각도: MINOR] :191 — wavlm-base-plus(group norm)에 attention_mask를 넘기며 배치 패딩 → 패딩이 있는 발화의 임베딩이 단독 추론과 약간 달라짐. 길이순 정렬 배치 또는 batch 1 권장(결과 무효 수준은 아님).
[심각도: MINOR] :273 — 승자 층·헤드를 평가에 쓰는 같은 holdout으로 선택(+2%p 기준 판단에 약한 낙관 편향). 보고 시 감안.

VERDICT: FAIL
