# dcc-lab (private)

DCC 2026 예선 개인 실험 자동화. 실험 코드·결과는 팀 저장소 `eigensinn-dcc2026/prelim`에 PR로 공유하고, 이 저장소에는 큐·상태·자동화 도구만 둔다.

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

## 2단계: 클라우드 자동 사이클 (GitHub Actions)

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

동시 실행: `config.json`의 `max_workers`(기본 2)만큼 Colab 러너가 병렬로 돈다. 워커는 노트북별 고정 이름(colab-a/b)이고 각자 `running/`의 자기 작업만 재개한다. 워치독이 워커별 heartbeat를 보고 필요한 노트북만 grokbot에 기동 요청한다.
