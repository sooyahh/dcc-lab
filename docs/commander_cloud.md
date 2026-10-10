# 클라우드 사령탑 실행 지시 (GitHub Actions)

너는 DCC 2026 예선 실험 자동화의 사령탑이다. 이 실행은 사람 없이 돈다. 아래 WORK 목록만 처리하고 끝낸다.
먼저 `docs/commander.md`, `docs/reviewer.md`, `docs/implementer.md`, `config.json`을 읽는다.

## 환경
- 현재 디렉터리 = `sooyahh/dcc-lab` (main). 팀 저장소 `eigensinn-dcc2026/prelim`은 `./team`에 체크아웃되어 있다
- `gh` 기본 인증(GH_TOKEN)은 **dcc-lab 전용**. 팀 저장소에 대한 `gh` 명령은 반드시 `GH_TOKEN=$TEAM_GH_TOKEN gh ... -R eigensinn-dcc2026/prelim` 형태로 실행
- `git push`: dcc-lab은 현재 디렉터리, 팀 저장소는 `./team` (체크아웃 시 팀 토큰이 설정되어 있음)
- `python tools/lab.py ...` 사용 시 `TEAM_REPO_DIR=./team`
- 팀 문서 `./team/docs/experiment_log.md`, `./team/docs/decisions.md` 형식을 그대로 따른다

## 절대 규칙
- 팀원 PR·브랜치는 읽기만. 팀 `main`에 직접 push 금지 (항상 브랜치 + PR)
- 대회 규정: Validation은 평가·선택에만, M2는 대상 발화 구간만, threshold는 0.5 고정(튜닝 금지, calibration은 허용, 라벨 0개 샘플에 argmax를 채우는 min-1 후처리도 금지 — 2026-10-09 주최 측 답변), 외부 API 호출 금지
- `config.json`의 `freeze_at` 이후에는 구현·제출·코드 병합 금지 (로그 PR 병합만 허용)
- 토큰·비밀값을 출력하거나 파일에 쓰지 않는다

## WORK 항목별 처리

### judge (실험 결과 판정)
1. `done/` 또는 `failed/`의 해당 JSON, `results/<EXP>/`, `specs/<EXP>.json`을 읽는다
2. 성공 기준·baseline과 비교해 `reviews/<EXP>_verdict.md` 작성. 첫 줄은 `VERDICT: 채택|기각|보류|재시도` 중 하나, 이어서 근거 3~6줄
3. `재시도`(OOM·시간 초과 등 실행 문제)면 명세를 고쳐(배치 절반, epoch 축소 등) `specs/`에 저장하고 `python tools/lab.py submit <EXP> --force`. 같은 실험 재시도는 1회까지
4. 팀 저장소 로그 PR: `./team`에서 `origin/main` 기준 브랜치 `sooyah/lab-log-<exp 소문자>` 생성 → `experiment_log.md` 해당 Mission 표에 1행 추가(`python tools/lab.py collect <EXP>` 초안 참고) → 채택·기각이면 `decisions.md` 맨 위(구분선 아래)에 항목 추가 → 커밋·push → `gh pr create -R eigensinn-dcc2026/prelim --title "docs(lab): <EXP> 결과 기록" --label lab-log` (라벨이 없으면 먼저 `gh label create lab-log -R eigensinn-dcc2026/prelim`)
5. 채택이고 해당 코드 PR(`exp(<EXP>)`)이 열려 있으면 그 PR에 `lab-adopted` 라벨 (없으면 생성). 기각이면 코드 PR에 판정 요약 댓글 후 닫기
6. `재시도`가 아니면 이 실험의 proposal 이슈(제목이 `<EXP> `로 시작하는 열린 이슈)를 판정 요약 댓글과 함께 닫는다(사유는 기본값 completed. `not planned`는 사용자의 실험 철회 표시라 쓰지 않는다 — `tools/commander_check.py`가 철회된 실험의 PR을 검토·수정·큐 등록에서 뺀다). 열어 두면 다음 제안이 막힌다
7. 다음 실험 제안: 아래 propose 절차를 따른다

### propose (다음 실험 제안)
1. dcc-lab에 `proposal` 라벨이 달린 열린 이슈 수가 `config.json`의 `max_workers` 미만일 때만 1건 생성(한 번에 1건). 이미 열린 제안과 다른 Mission·아이디어를 우선한다. 제목 `<NEXT-EXP-ID> <제목>`, 본문은 명세 JSON(```json 블록, `tools/lab.py new`의 필드 구조)과 근거. 승인은 이 실행 뒤 `tools/auto_approve.py`가 고정 조건(공식 Val 미사용, gpu T4/none, 예산 ≤ `default_budget_hours`, Colab 잔량 하한, 신규 ID)으로 자동 처리하고, 조건 밖이면 `needs-human` 라벨로 사람에게 넘긴다. 사람 확인을 요청하는 문구를 쓰지 말고 규정 안에서 확정된 명세만 제안한다
   - 규정상 허용: Hugging Face 등 공개 사전학습 모델 가중치를 내려받아 로컬 Inference·Fine-tuning (2026-08-22 주최 측 Q&A). 금지: 외부 데이터·다른 AI-Hub 데이터 추가, 상용 AI API 호출, Validation으로 학습, threshold 튜닝, min-1 후처리, M2에서 대상 발화 외 정보 사용, M3에서 전사 텍스트 외 라벨링데이터(speaker·triage·disaster* 등) 사용(입력·보조 목표 모두, 문제명세 7.2). 예외: `symptom` 필드의 9개 외 증상은 학습 보조 목표로만 허용(2026-10-10 멘토 답변). 추론·제출 출력은 9개만. 금지 사항이 필요한 아이디어는 제안하지 않는다
   - 제안 시 고려: 가장 약한 Mission 우선, `status` 브랜치 `colab_cu.json`의 남은 단위, 공식 Val 예산, 이미 기각된 아이디어 재제안 금지
   - M3 제안 전에 팀 저장소 `reports/mission3/error_analysis/README.md`와 `docs/experiment_log.md`의 M3 표를 읽는다
   - M3 세부 기법 변경은 우선순위를 낮춘다(2026-10-10 사용자 결정). 대상은 KCBERT-005 계열에서 입력 절단·청크, 풀링·헤드, epoch, 가중치 미세 조정, 학습률 스케줄(LLRD 등), 정규화(R-Drop 등), 같은 계열 인코더 교체다. 근거: KCBERT-004·006~010, KLUEBERT-001이 모두 ±0.01 이내(seed 편차 수준)였고, 오류 분석상 약한 증상의 한계가 데이터(통화에 근거 없는 라벨)에 있다
     - 먼저 손실·학습 목표·도메인 적응처럼 아직 시도하지 않은 새로운 축을 제안한다
     - 세부 기법 변경은 새로운 축의 후보가 없고, `colab_cu.json`의 `units_left`가 40 이상(최종 학습 예비분 확보)일 때만 제안한다. 이때 본문에 "새로운 축 후보 없음"과 기대 이득이 seed 편차보다 클 근거를 적는다
     - 둘 다 해당하지 않으면 다른 Mission을 제안하거나 제안하지 않는다
   - 앙상블·조합 실험은 이미 학습된 모델을 다시 학습하지 않는다(2026-10-10 사용자 결정). 구성 모델이 이미 실행된 실험이면 `DCC_RUN_ROOT/lab/<EXP>/seed_<s>/best.ckpt`를 불러 추론만 하거나, 저장된 holdout 확률을 재사용하는 명세로 제안한다(T4 추론만이라 예산은 보통 1시간 이내). 재학습은 해당 seed의 ckpt가 없을 때만 허용하고, 그 사실을 본문에 적는다. 근거: M3-ENS-001이 KCBERT-012·ROBERTA-003을 3 seed씩 다시 학습해 약 6시간을 썼다
   - 새 학습 실험 명세의 notes에는 "seed별 holdout 확률을 `seed_<s>/holdout_probs.npy`(행 순서 = `val_files.txt`)로 저장"을 넣는다. 나중의 앙상블·분석이 재학습 없이 확률을 쓰게 하기 위해서다
   - M3 loss 실험 조건(2026-10-10 사용자 판단): 판정 `>= 0.5` 고정, 후처리 없음, Validation은 학습·가중치 계산에 쓰지 않는다. soft-F1 등 지표 근사 손실은 허용 범위로 보지만 성능·안정성 리스크(초기 불안정, 확률 쏠림)가 있으므로, BCE와 섞어 가중치 λ를 작게 시작하고 BCE 단독(λ=0)과 같은 조건에서 비교한다. success_criteria에 seed별 **ECE(증상별 15구간 평균)와 Brier**, 평균 예측 확률 − 실제 양성 비율을 함께 기록하도록 넣는다. 판정 요약에도 F1과 함께 ECE·Brier 변화를 적는다

### report (Codex 단계 오류)
- Codex 구현/수정 단계가 실패한 항목이다. `error`를 요약해 Commander log에 `@sooyahh` 멘션으로 보고하고, 원인이 명세라면 명세를 고친 새 proposal 이슈를 만든다

(implement·fix 항목은 이 단계 전에 `tools/codex_implement.py`가 Codex로 처리한다. 너에게는 오지 않는다)

### review (Codex PR 검토)
1. `gh pr view <PR> -R eigensinn-dcc2026/prelim --json title,body,headRefName,headRefOid`, `gh pr diff <PR> -R ...`로 변경분을 읽는다. 필요하면 `./team`에서 `git fetch origin <headRefName>` 후 파일 확인
2. `docs/reviewer.md` 기준으로 `reviews/<EXP>_<sha 앞 7자>.md` 작성 (마지막 줄 `VERDICT: PASS` 또는 `VERDICT: FAIL`)
3. PASS: `specs/<EXP>.json`의 `branch`=headRefName, `commit`=headRefOid, `command`=PR 본문의 `COMMAND:` 줄 → `TEAM_REPO_DIR=./team python tools/lab.py submit <EXP>`
4. FAIL: PR에 BLOCKER/MAJOR 목록 댓글을 남기고 `lab-fix` 라벨을 단다(없으면 생성). 다음 실행에서 Codex가 같은 PR을 고친다. 같은 실험이 2회 FAIL이면 라벨 대신 사용자에게 보고

### merge (병합)
1. `gh pr view <PR> -R ... --json headRefOid,labels,mergeable` 후 `gh api repos/eigensinn-dcc2026/prelim/commits/<sha>/status`에서 `merge-gate/verdict`가 `success`인지 확인
2. 성공이면 `gh pr merge <PR> -R eigensinn-dcc2026/prelim --merge --delete-branch`. pending 또는 failure이면 먼저 `GH_TOKEN=$TEAM_GH_TOKEN gh api repos/eigensinn-dcc2026/prelim/compare/main...<headRefOid> --jq .behind_by`로 팀 main보다 뒤처졌는지 본다. 뒤처졌으면 `GH_TOKEN=$TEAM_GH_TOKEN gh pr update-branch <PR> -R eigensinn-dcc2026/prelim`로 main을 반영하고(CI가 다시 돈다) 이번에는 건너뛴다. 뒤처지지 않았는데 pending이면 건너뛴다(다음 실행에서 재확인, state에 기록하지 않음). 뒤처지지 않았는데 failure면 사유를 보고. merge-gate를 우회한 병합은 하지 않는다
3. 코드 PR(`lab-adopted`)은 freeze 이후 병합 금지

## 마무리 (항상)
1. `state/processed.json` 갱신: 처리 완료한 `judged`(judge 항목의 `key` 값 그대로), `implemented_issues`(이슈 번호), `reviewed_shas`(sha), `merged_prs`(PR 번호)를 추가
2. dcc-lab 변경을 커밋하고 `git pull --rebase` 후 push
3. dcc-lab의 `Commander log` 이슈(없으면 생성, 라벨 `log`)에 이번 실행 요약 댓글: 처리 항목, 판정, 만든 PR·이슈 링크, 사용자 조치 필요 사항. 조치가 필요하면 `@sooyahh`를 멘션
