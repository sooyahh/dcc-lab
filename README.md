# dcc-lab — AI 실험 자동화 환경 (DCC 2026 예선)

데이터+AI 크리에이터 캠프 2026 대학부 예선(119 신고 전화 음성·전사 데이터로 응급상황 인식)에서,
데이터 분석이 처음인 팀원들도 실험 아이디어를 바로 검증할 수 있도록 직접 구축한 실험 자동화 환경입니다.

- **역할 분담**: Claude가 실험 명세 작성·검토·판정, Codex가 구현, Cursor가 오류 수정, Colab이 GPU 실행, grokbot이 러너 기동·감시
- **운영 원칙**: 채택·기각 기준을 실험 전에 정하고, AI의 완료 보고가 아니라 실제 산출물(지표 파일·실행 로그)로만 완료를 판정
- **팀 최종 결과**: 신고자 성별 분류 Accuracy 98.10% · 신고자/상황실 화자 구분 91.49% · 증상 분류 Macro F1 0.6534
- **둘러보기**: `docs/` 각 AI의 역할 규칙 · `specs/` 실험 명세 · `reviews/` 검토 기록 · `results/` 실험 결과

> 실험 코드와 데이터는 팀 저장소(비공개)에 있으며, 이 저장소에는 큐·상태·자동화 도구만 있습니다.
> 대회 규정에 따라 제출 모델은 외부 상용 AI API를 호출하지 않으며, AI 도구는 개발 과정에서만 사용했습니다.

---

## 운영 메모 (원문)

DCC 2026 예선 개인 실험 자동화. 실험 코드·결과는 팀 저장소 `eigensinn-dcc2026/prelim`(비공개)에 PR로 공유하고, 이 저장소에는 큐·상태·자동화 도구만 둔다.

| 역할 | 담당 | 규칙 |
|---|---|---|
| 사령탑 (명세·검토·판정·병합) | Claude | `docs/commander.md`, `docs/reviewer.md` |
| 구현 (이슈 → PR) | Codex cloud | `docs/implementer.md` |
| GPU 실행 | Colab 러너 | `runner/lab_runner.py`, `runner/lab_worker.ipynb`(colab-a), `runner/lab_worker_2.ipynb`(colab-b) |
| 러너 기동·감시·사용량 보고 | grokbot | `grokbot/instructions.md` |

```
queue/ → running/ → done/ | failed/        (main 브랜치, 러너가 claim/finish 커밋)
results/<EXP>/metrics.json, run_tail.log   (러너가 push)
status 브랜치: heartbeat_<worker>.json, colab_cu.json (러너가 lease push, 15분 주기)
Drive dcc_lab/status/: heartbeat_<worker>.json, queue_pending.json, colab_cu.json, runner_issue.json (grokbot 채널)
Drive dcc_runs/lab/<EXP>/: ckpt·로그 (재개용)
```

`python tools/lab.py {new|submit|status|collect}` — 자세한 사용법은 파일 상단 docstring.

### 2단계: 클라우드 자동 사이클 (GitHub Actions)

```
proposal 이슈(Claude) ──사용자 approved 라벨──▶ 팀 저장소 이슈 @codex ──▶ Codex PR
   ▲                                                                   │
   │                                            Claude 검토 PASS → queue/ (FAIL → @codex 수정)
   │                                                                   ▼
Claude 판정 → 팀 로그 PR(자동 병합) + 다음 proposal ◀── done/ ◀── Colab 러너 ◀── grokbot(watchdog 웹훅)
```

| 워크플로 | 주기 | LLM |
|---|---|---|
| `commander.yml` | 결과 push, 라벨 이벤트, 매시 17분 | 할 일이 있을 때만 Claude (`tools/commander_check.py`가 선판단) |
| `watchdog.yml` | 30분, 큐 push | 없음 (`tools/watchdog.py`) |

Secrets: `CLAUDE_CODE_OAUTH_TOKEN`, `TEAM_REPO_TOKEN`, `GROKBOT_WEBHOOK_URL`. 실행 기록은 `Commander log` 이슈.

동시 실행: `config.json`의 `max_workers`(2026-10-12부터 1 — Colab GPU 세션 1개 제한, 이때 colab-a가 모든 작업을 이어받음)만큼 Colab 러너가 병렬로 돈다. 워커는 노트북별 고정 이름(colab-a/b)이고 각자 `running/`의 자기 작업만 재개한다. 워치독이 워커별 heartbeat를 보고 필요한 노트북만 grokbot에 기동 요청한다.
