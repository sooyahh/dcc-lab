# dcc-lab — AI 실험 자동화 환경 (DCC 2026 예선)

데이터+AI 크리에이터 캠프 2026 대학부 예선(119 신고 전화 음성·전사 데이터로 응급상황 인식)에서,
데이터 분석이 처음인 팀원들도 실험 아이디어를 바로 검증할 수 있도록 직접 구축한 실험 자동화 환경입니다.

- **역할 분담**: Claude가 실험 명세 작성·검토·판정, Codex가 구현, Cursor가 오류 수정, Colab이 GPU 실행, grokbot이 러너 기동·감시
- **운영 원칙**: 채택·기각 기준을 실험 전에 정하고, AI의 완료 보고가 아니라 실제 산출물(지표 파일·실행 로그)로만 완료를 판정
- **팀 최종 결과**: 신고자 성별 분류 Accuracy 98.10% · 신고자/상황실 화자 구분 91.49% · 증상 분류 Macro F1 0.6534
- **둘러보기**: `docs/` 각 AI의 역할 규칙 · `specs/` 실험 명세 · `reviews/` 검토 기록 · `results/` 실험 결과

## 운영 현황과 검증 가능한 자동화 성과

**상태:** DCC 2026 대학부 예선 기간에 사용한 실험 오케스트레이션 환경의 **기록 보존용 공개본**입니다. 팀의 제출물 동결 시각은 **2026-10-14 09:00 KST**(`config.json`)였고, 확인된 GitHub Actions 마지막 실행 기록은 **2026-10-14**입니다. 워크플로 스케줄 정의가 저장소에 남아 있어도 현재 자동화가 계속 가동 중이라는 의미는 아닙니다. Actions의 현재 활성화 설정은 여기서 검증하지 않았습니다.

### 기록으로 확인되는 산출물

아래 숫자는 **2026-11-05 공개 저장소의 파일 스냅샷**에서 직접 집계한 것이며, 서로 다른 개념을 합산하지 않습니다.

| 항목 | 확인된 기록 | 근거 |
|---|---:|---|
| 실험 명세 | **71개** | [`specs/`](specs/)의 JSON |
| 완료 상태 파일 | **64개** | [`done/`](done/)의 JSON: 모델 실험 54, 인프라 작업 3, smoke test 7 |
| 실패 상태 파일 | **17개** | [`failed/`](failed/)의 JSON; 재시도 과정의 기록이므로 17개 실험이 최종 실패했다는 뜻은 아님 |
| 실험 결과 지표 | **64개** | [`results/`](results/) 하위 `metrics.json` |
| 판정 근거 문서 | **55개** | [`reviews/`](reviews/)의 `*_verdict.md` |

- 실패 기록 17개 중 **15개와 같은 실험 ID**에 대해 별도의 완료 기록이 존재합니다. 이는 재시도·복구 기록을 보여주지만, 실패 17건 모두가 자동 복구됐다는 주장은 아닙니다.
- **큐 3개, 실행 중 2개** 상태 파일도 공개 스냅샷에 남아 있습니다. 이는 *마지막 저장 상태*일 뿐 현재 GPU 작업 실행이나 미완료 프로젝트 수를 뜻하지 않습니다.
- 완료 기록에는 smoke test와 인프라 점검이 포함되므로 **64건 모두를 학습 실험이나 성능 개선으로 계산하면 안 됩니다.** GitHub Actions 호출 횟수 또한 실험 성공 횟수와 다릅니다.

### 자동화가 맡은 단계와 통제 방식

1. **실험 제안·구현·리뷰:** `specs/<EXP>.json`에 가설, 기준 모델, 변경점, 채택 조건, GPU 예산을 기록하고, Codex PR을 코드·규정·데이터 누수 관점에서 검토합니다. [검토 규칙](docs/reviewer.md)
2. **GPU 실행·중단 복구:** GitHub 상태 큐에서 작업을 claim하고 Colab 러너가 실행하여 `metrics.json`과 실행 로그를 남깁니다. 작업 중단·재시도 상태를 분리합니다. [러너](runner/)
3. **결과 판정:** 실험 전에 정한 기준과 저장된 산출물로 채택·기각·보류를 결정합니다. **AI의 완료 메시지만으로 성공 처리하지 않습니다.** 예컨대 [M1-ECAPA-001 기각 판정](reviews/M1-ECAPA-001_verdict.md)은 개선폭과 유의성 기준 미달을 기록합니다.
4. **사용자·대회 규정 통제:** 제안 승인 단계, 공식 Validation 사용 제한, 실험별 재시도 상한, 제출 동결 시각 및 자원 예산을 운영 규칙에 둡니다. [운영 규칙](docs/commander.md) · [설정](config.json)

**성과 해석:** 이 저장소가 입증하는 것은 *명세 → 구현·검토 → GPU 실행 → 결과 파일 → 판정*의 작업 흐름과 기록입니다. 상단의 M1/M2/M3 최종 정확도·F1은 **DCC 팀의 모델 성능**으로, 자동화 시스템 단독의 성능 향상이나 생산성 절감 효과를 측정한 수치가 아닙니다. 사람이 절약한 시간·비용에 대한 비교 실험도 수행하지 않았으므로 수치를 주장하지 않습니다.

---

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
