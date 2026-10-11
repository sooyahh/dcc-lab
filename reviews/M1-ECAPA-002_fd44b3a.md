# M1-ECAPA-002 검토 (PR #150, fd44b3a)

1. Validation 누수: OK — Training TL_/TS_ zip만 사용(xvec-001 `prepare_rows` 재사용), StandardScaler는 파이프라인 내부라 fold train에서만 추정
2. 분할 누수: OK — 성별 층화 5-fold, call_id 중복 시 실패(1통화=1행). seed 42 holdout은 캐시 split.json과 대조
3. 입력 필드: OK — 신고자 구간 음성만 사용, 성별은 정답으로만
4. M2: 해당 없음
5. 외부 데이터·네트워크: OK — 고정 revision을 `$DCC_RUN_ROOT/models`에만 받음(허용 범위). 단 아래 MAJOR의 오버라이드 누락 참고
9. requirements.txt: `speechbrain==1.0.3` 1줄 추가뿐 — 허용
6. 실행 계약: 청크·fold×헤드 단계 재개, metrics.json·best.ckpt 작성 OK
7. 명세 일치: 헤드 c/h/i/j, 창 규칙, 5-fold(2026), McNemar, 판정 기준 OK
8. 버그: 이전 MAJOR(`stems` 필수)는 해결됨. 캐시 계약(청크 이름·필드·rows_sha256·split)은 bb9921b의 m1-xvec-002.py와 일치. 아래 MAJOR 1건

- [MAJOR] scripts/lab/m1-ecapa-002.py `prepare_model` (`EncoderClassifier.from_hparams(source=str(root), savedir=str(root), ...)`) — Drive(`/content/drive/...`)는 symlink 미지원이다. M1-ECAPA-001 1·2차 실행이 정확히 이 호출 형태에서 `OSError: [Errno 95] ... label_encoder.txt -> label_encoder.ckpt`(speechbrain `link_with_strategy`)로 실패했다. 기본 `local_strategy`가 symlink라 이 실험도 모델 로드에서 즉시 실패한다. 또한 `overrides={"pretrained_path": ...}`가 없어 upstream YAML의 HF 경로로 원격 조회할 수 있고(주석은 "local custom module prevent remote fallback"라 하나 구현 없음), `snapshot_download`에 `allow_patterns`가 없어 불필요 파일까지 받는다. 고칠 방법: 통과한 m1-ecapa-001.py(`origin/sooyah/lab-m1-ecapa-001`)의 `prepare_model`·`stage_model`(필수 5파일 allow_patterns, `LAB_WORK`로 원자적 복사, `source=savedir=<로컬 복사본>`, `overrides={"pretrained_path": local}`, `local_strategy=LocalStrategy.COPY`)을 그대로 재사용
- [MINOR] `from speechbrain.inference.speaker import EncoderClassifier` — 001은 `speechbrain.inference.classifiers`를 씀(1.0.3에서 둘 다 되면 무방). 001과 맞추는 편이 안전

VERDICT: FAIL
