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
- 대회 규정: Validation은 평가·선택에만, M2는 대상 발화 구간만, threshold는 0.5 고정(튜닝 금지, calibration은 허용), 외부 API 호출 금지
- `config.json`의 `freeze_at` 이후에는 구현·제출·코드 병합 금지 (로그 PR 병합만 허용)
- 토큰·비밀값을 출력하거나 파일에 쓰지 않는다

## WORK 항목별 처리

### judge (실험 결과 판정)
1. `done/` 또는 `failed/`의 해당 JSON, `results/<EXP>/`, `specs/<EXP>.json`을 읽는다
2. 성공 기준·baseline과 비교해 `reviews/<EXP>_verdict.md` 작성. 첫 줄은 `VERDICT: 채택|기각|보류|재시도` 중 하나, 이어서 근거 3~6줄
3. `재시도`(OOM·시간 초과 등 실행 문제)면 명세를 고쳐(배치 절반, epoch 축소 등) `specs/`에 저장하고 `python tools/lab.py submit <EXP> --force`. 같은 실험 재시도는 1회까지
4. 팀 저장소 로그 PR: `./team`에서 `origin/main` 기준 브랜치 `sooyah/lab-log-<exp 소문자>` 생성 → `experiment_log.md` 해당 Mission 표에 1행 추가(`python tools/lab.py collect <EXP>` 초안 참고) → 채택·기각이면 `decisions.md` 맨 위(구분선 아래)에 항목 추가 → 커밋·push → `gh pr create -R eigensinn-dcc2026/prelim --title "docs(lab): <EXP> 결과 기록" --label lab-log` (라벨이 없으면 먼저 `gh label create lab-log -R eigensinn-dcc2026/prelim`)
5. 채택이고 해당 코드 PR(`exp(<EXP>)`)이 열려 있으면 그 PR에 `lab-adopted` 라벨 (없으면 생성). 기각이면 코드 PR에 판정 요약 댓글 후 닫기
6. `재시도`가 아니면 이 실험의 proposal 이슈(제목이 `<EXP> `로 시작하는 열린 이슈)를 판정 요약 댓글과 함께 닫는다. 열어 두면 다음 제안이 막힌다
7. 다음 실험 제안: 아래 propose 절차를 따른다

### propose (다음 실험 제안)
1. dcc-lab에 `proposal` 라벨이 달린 열린 이슈가 없을 때만 1건 생성. 제목 `<NEXT-EXP-ID> <제목>`, 본문은 명세 JSON(```json 블록, `tools/lab.py new`의 필드 구조)과 근거. 사용자가 `approved` 라벨을 달아야 진행된다
   - 제안 시 고려: 가장 약한 Mission 우선, `status` 브랜치 `colab_cu.json`의 남은 단위, 공식 Val 예산, 이미 기각된 아이디어 재제안 금지

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
2. 성공이면 `gh pr merge <PR> -R eigensinn-dcc2026/prelim --merge --delete-branch`. 아직 pending이면 이번에는 건너뛴다(다음 실행에서 재확인, state에 기록하지 않음). failure면 사유를 보고
3. 코드 PR(`lab-adopted`)은 freeze 이후 병합 금지

## 마무리 (항상)
1. `state/processed.json` 갱신: 처리 완료한 `judged`(judge 항목의 `key` 값 그대로), `implemented_issues`(이슈 번호), `reviewed_shas`(sha), `merged_prs`(PR 번호)를 추가
2. dcc-lab 변경을 커밋하고 `git pull --rebase` 후 push
3. dcc-lab의 `Commander log` 이슈(없으면 생성, 라벨 `log`)에 이번 실행 요약 댓글: 처리 항목, 판정, 만든 PR·이슈 링크, 사용자 조치 필요 사항. 조치가 필요하면 `@sooyahh`를 멘션
