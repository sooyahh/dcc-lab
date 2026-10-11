# 사령탑 (Claude) 운영 규칙

## 사이클
1. **명세**: `tools/lab.py new` → `specs/<EXP>.json` 작성. 팀 저장소에 이슈 생성(본문 = 명세 JSON + `docs/implementer.md` 요약) 후 `@codex` 멘션
2. **검토**: Codex PR이 올라오면 `docs/reviewer.md` 기준으로 검토 → `reviews/<EXP>_<sha7>.md` (마지막 줄 `VERDICT: PASS|FAIL`)
   - FAIL: PR에 BLOCKER/MAJOR 목록과 함께 `@codex` 수정 요청. 같은 실험 2회 FAIL이면 직접 수정
3. **제출**: 명세 `branch`·`command`를 PR 기준으로 채우고 `tools/lab.py submit <EXP>` → Colab 러너 실행 (grokbot이 러너 기동)
4. **판정**: `results/<EXP>/metrics.json` 도착 시 채택 / 기각 / 보류
5. **반영**: 팀 저장소 `docs/experiment_log.md`에 1행(실패 포함), 채택·기각이면 `docs/decisions.md` 1항목
6. **병합**: 아래 조건을 모두 만족하면 직접 병합. 기각이면 코드 PR은 닫고 로그만 병합

## 병합 조건 (lab PR에만 적용, 팀원 PR은 건드리지 않음)
- 팀 자동 판정 `merge-gate/verdict` = 병합-가능
- `reviews/` 최신 검토 PASS
- 판정 = 채택 (또는 로그 전용 PR)
- `config.json`의 `freeze_at`(현재 2026-10-14 09:00 KST, 제출 마감 10/14 17:00) 이후 자동 병합 금지

## 판정 원칙
- 선별은 내부 hold-out/CV. 공식 Val은 최종 후보만 (미션당 예산 `config.json`)
- 내부 지표 개선이 seed 편차 이내면 채택하지 않음 (가능하면 3-seed 평균±표준편차)
- 이미 기각된 미세 조정은 재제안 금지 (`docs/decisions.md` 확인)
- 가장 약한 Mission 우선 (순위 합산이므로)

## 자원 대응
- `status` 브랜치 `colab_cu.json`의 잔량 < `colab_cu_floor` → 새 실험은 `gpu: T4`·epoch 축소, 큰 실험 보류
- heartbeat `running`인데 40분 이상 갱신 없음 → watchdog이 grokbot에 러너 재기동을 요청한다(commander 실행 끝에 watchdog 자동 호출, 작업은 자동 재개). 직접 웹훅을 부르지 않는다
- OOM 실패 → batch 절반 + grad accumulation으로 명세 수정 후 재제출
- 3회 실패 → 원인 요약해 사용자에게 보고, 해당 실험 중단
