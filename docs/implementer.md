# 구현자(Codex cloud) 작업 지시 (실험 코드 작성)

당신은 DCC 2026 예선 팀 저장소에서 **실험 코드만** 작성한다. 실험 설계와 채택 판단은 사령탑(Claude)이 하고,
실행은 Colab 러너가 한다. 명세 파일 `lab_ops/specs/<EXP_ID>.json`을 읽고 그 범위만 구현한다.

## 작업 절차
1. 명세는 이 지시를 부른 GitHub 이슈 본문(JSON)에 있다. 팀 저장소 `eigensinn-dcc2026/prelim`의 최신 `main`에서 작업한다
2. 실험 스크립트는 `scripts/lab/<exp_id 소문자>.py` 한 파일을 기본으로 하고, 재사용 로직만 `src/dcc_data/`에 추가
3. 의존성이 새로 필요하면 `requirements.txt`에 추가 (버전 고정)
4. PR 제목: `exp(<EXP_ID>): <한 줄 요약>`. PR 본문 마지막 줄은 정확히 `COMMAND: <저장소 루트에서 실행할 명령>` (출력 경로는 `$LAB_OUT` 그대로)
5. 학습을 직접 돌리지 말 것. 10초 내 끝나는 `--smoke` 실행과 import 확인만 허용
6. 검토에서 `@codex` 수정 요청이 오면 같은 PR 브랜치에 커밋을 추가한다

## 실행 계약 (러너가 강제함 — 어기면 실패 처리)
- 작업 디렉터리 = 저장소 루트. `PYTHONPATH`에 `src/`가 들어 있다.
- 환경 변수: `LAB_EXP_ID`, `LAB_OUT`(Drive, 영구 보존), `LAB_WORK`(/content 로컬 디스크, 임시), `DCC_RUN_ROOT`
- 데이터 경로는 `dcc_data.colab_env.find_data_root()`로 찾는다. 하드코딩 금지
- Drive에서 작은 파일 수천 개를 직접 읽지 말 것. 큰 파일로 묶어 `LAB_WORK`로 복사 후 사용
  - 묶음은 이미 있다: `find_data_root()/<Training|Validation>/<폴더>.zip` (예: `Training/TL_서울_구급.zip` = 라벨 JSON, `Training/TS_서울_구급.zip` = wav, Validation은 `VL_`/`VS_`). zip 안 경로는 `<폴더>/...`. 이 zip 1개를 `LAB_WORK`로 복사해 압축을 풀어 쓴다. 낱개 파일 폴더를 rglob하지 말고 `<split>/<폴더>.zip`을 직접 지정한다
- **재개 가능해야 한다**: 런타임은 언제든 끊긴다. 같은 명령을 다시 실행하면
  - 끝난 단계(특징 추출, 각 seed 학습 등)는 `LAB_OUT`의 산출물을 보고 건너뛰고
  - 학습 중이던 것은 `LAB_OUT/ckpt_last.pt`(모델·옵티마이저·스케줄러·epoch·RNG 상태)에서 이어 간다
  - epoch마다 `ckpt_last.pt`를 임시 파일에 쓴 뒤 `os.replace`로 교체
  - **큰 파일(체크포인트 등 100MB 이상)은 Drive에 직접 쓰지 않는다**: `LAB_WORK`(로컬)에 `torch.save` → `shutil.copyfile`로 `LAB_OUT` 안의 임시 이름(`<이름>.tmp`)에 복사 → 크기 확인 → `os.replace`. 복사·교체는 `OSError` 시 최대 5회 재시도(2·4·8·16·32초). Drive FUSE에 수 GB를 바로 쓰면 임시 파일이 사라지는 오류가 난다(M3-XLMR-001, 2026-10-11)
  - epoch이 20분보다 길면 epoch 안에서도 약 15분마다 `ckpt_last.pt`(step 위치·샘플 순서 포함)를 저장해 그 step부터 이어 간다. 런타임이 약 85분 간격으로 끊긴 사례가 있어(M3-E5-001, 2026-10-11) epoch 단위 저장만으로는 끝나지 않을 수 있다
  - `ckpt_last.pt`에 옵티마이저 상태까지 담으면 large 모델은 수 GB가 된다. 재개에 필요한 것만 담고, `best.ckpt`는 모델 가중치만(fp16 허용) 저장한다
- 종료 시 `LAB_OUT/metrics.json`을 반드시 쓴다:
  ```json
  {"exp_id": "...", "primary_metric": {"name": "accuracy", "value": 0.8731, "split": "internal_holdout"},
   "metrics": {...}, "seed": 42, "train_rows": 0, "eval_rows": 0,
   "official_val": null, "ckpt": "best.ckpt", "notes": ""}
  ```
  `split`은 `internal_holdout` | `internal_cv` | `official_val` 중 하나. 공식 Val 점수는 명세의
  `uses_official_val`이 true일 때만 계산해 `official_val`에 넣는다.
- 최종 모델은 `LAB_OUT/best.ckpt` (`.pt/.pth/.ckpt` 확장자만 허용, sklearn/LGBM은 `joblib.dump`로 `.ckpt`에 저장)

## 대회 규정 (위반 = 실격 가능, 예외 없음)
- 학습은 **Training(서울) 데이터만**. 외부 데이터·다른 AI-Hub 데이터 금지
- **공식 Validation은 평가·early stopping·ckpt/하이퍼파라미터 선택·앙상블 가중치에만**. 학습 데이터에 섞거나 backprop 금지.
  가능하면 early stopping도 Training 내부 call_id 기준 hold-out으로 하고 공식 Val은 마지막 평가만
- 분할은 **call_id 단위** (같은 통화가 train/holdout에 동시에 들어가면 안 됨)
- 입력 필드 화이트리스트: M1 = 음성 + startAt/endAt/Speaker, M2 = 음성 + startAt/endAt, M3 = 전사 text
- **M2는 대상 발화(startAt~endAt) 구간 정보만** 사용. 같은 통화의 다른 발화로 만든 값(길이 비율, 통화 단위 정규화,
  발화 순서, 통화 내 클러스터링)은 금지 (주최 측 공식 답변, 2026-10-05)
- 전처리 통계(정규화 평균·분산 등)는 Training에서만 추정
- 사전학습 모델은 HF 등 공개 모델을 로컬로 받아 사용. 추론 코드에서 외부 API·네트워크 호출 금지
- seed 고정 (`random`, `numpy`, `torch`, `cuda`), 사용한 seed를 metrics.json에 기록

## 사전학습 모델 가중치 (사령탑 결정, 2026-10-08)
- 대회 규정상 Hugging Face 등 **공개 사전학습 모델을 내려받아** 자체 환경에서 쓰는 것은 허용된다(외부 API 호출과 다름)
- 첫 실행 때 `huggingface_hub.snapshot_download(repo_id, revision=<고정 커밋 해시>, local_dir=$DCC_RUN_ROOT/models/<모델이름>)`으로 **Drive 영구 경로**에 받고, 이미 있으면 건너뛴다. 이후 로드는 그 경로에서 `local_files_only=True`
- `main()` 시작 직후(데이터 준비 전) 모델 경로를 확인·준비해서, 문제가 있으면 수십 분 작업 전에 바로 실패하게 한다
- 제출용 추론 코드는 이 로컬 경로만 읽고 네트워크를 쓰지 않는다

## requirements.txt
- 이미 있는 패키지(또는 그 의존성으로 설치되는 패키지: joblib, numpy 등)를 추가·버전 고정하지 않는다. 팀 공용 파일이라 다른 팀원 환경을 바꾼다
- 정말 새 패키지가 필요할 때만 한 줄 추가
