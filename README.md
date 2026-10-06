# dcc-lab (private)

DCC 2026 예선 개인 실험 자동화. 실험 코드·결과는 팀 저장소 `eigensinn-dcc2026/prelim`에 PR로 공유하고, 이 저장소에는 큐·상태·자동화 도구만 둔다.

| 역할 | 담당 | 규칙 |
|---|---|---|
| 사령탑 (명세·검토·판정·병합) | Claude | `docs/commander.md`, `docs/reviewer.md` |
| 구현 (이슈 → PR) | Codex cloud | `docs/implementer.md` |
| GPU 실행 | Colab 러너 | `runner/lab_runner.py`, `runner/lab_worker.ipynb` |
| 러너 기동·감시·사용량 보고 | grokbot | `grokbot/instructions.md` |

```
queue/ → running/ → done/ | failed/        (main 브랜치, 러너가 claim/finish 커밋)
results/<EXP>/metrics.json, run_tail.log   (러너가 push)
status 브랜치: heartbeat.json, colab_cu.json (러너가 force-push, 15분 주기)
Drive dcc_lab/status/: heartbeat.json, queue_pending.json, colab_cu.json, runner_issue.json (grokbot 채널)
Drive dcc_runs/lab/<EXP>/: ckpt·로그 (재개용)
```

`python tools/lab.py {new|submit|status|collect}` — 자세한 사용법은 파일 상단 docstring.
