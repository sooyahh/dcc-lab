"""Token-free auto-approval of experiment proposals (runs in commander.yml after the Claude step).

For each open `proposal` issue without `approved` / `needs-human`:
  parse the ```json spec block and check hard limits below.
  pass -> label `approved` + comment, then dispatch commander once so Codex starts now
          (labels added with GITHUB_TOKEN do not fire relay.yml, workflow_dispatch does run).
  fail -> label `needs-human` + comment with reasons (@sooyahh). The user approves by hand.
Rule questions (pretrained HF weights etc.) are settled in docs/commander_cloud.md, not here.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
CFG = json.loads((LAB / "config.json").read_text(encoding="utf-8"))
REPO = os.environ.get("GITHUB_REPOSITORY", "sooyahh/dcc-lab")
REQUIRED = ("exp_id", "mission", "title", "hypothesis", "baseline", "success_criteria", "gpu", "budget_hours")


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def colab_cu() -> dict:
    subprocess.run(["git", "-C", str(LAB), "fetch", "-q", "origin", "status"], check=False)
    raw = subprocess.run(["git", "-C", str(LAB), "show", "origin/status:colab_cu.json"],
                         capture_output=True, text=True).stdout
    return json.loads(raw) if raw else {}


def problems(issue: dict, cu: dict) -> list[str]:
    m = re.search(r"```json\s*(\{.*?\})\s*```", issue["body"], re.S)
    if not m:
        return ["본문에 ```json 명세 블록이 없음"]
    try:
        spec = json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        return [f"명세 JSON 파싱 실패: {exc}"]
    out = [f"필드 누락: {k}" for k in REQUIRED if k not in spec]
    exp = str(spec.get("exp_id", ""))
    if issue["title"].split()[:1] != [exp]:
        out.append("이슈 제목 첫 단어와 exp_id 불일치")
    if (LAB / "specs" / f"{exp}.json").exists():
        out.append(f"{exp}는 이미 실행된 ID (재제안 금지)")
    if spec.get("uses_official_val"):
        out.append("공식 Validation 사용 실험 (예산 관리상 사람 승인)")
    rates = CFG.get("gpu_cu_per_hour", {"none": 0, "T4": 1.1})
    gpu = str(spec.get("gpu", "T4"))
    gpu = "none" if gpu.lower() == "none" else gpu.upper()
    if gpu not in rates:
        out.append(f"gpu={spec.get('gpu')} (자동 승인은 {'/'.join(rates)}만, 그 밖은 사람 승인)")
    hours = float(spec.get("budget_hours") or 0)
    if not 0 < hours <= CFG["default_budget_hours"]:
        out.append(f"budget_hours={hours} (0 초과 {CFG['default_budget_hours']} 이하만)")
    if "units_left" not in cu:
        out.append("status 브랜치 colab_cu.json 없음 (Colab 잔량 확인 불가)")
    else:
        after = cu["units_left"] - hours * float(rates.get(gpu, 11))      # this job's GPU rate, not the current total
        if after < CFG["colab_cu_floor"]:
            out.append(f"실행 후 Colab 잔량 예상 {after:.1f} < 하한 {CFG['colab_cu_floor']}")
    return out


def main() -> None:
    if dt.datetime.now(dt.timezone.utc) > dt.datetime.fromisoformat(CFG["freeze_at"]):
        print("frozen: no auto-approval")
        return
    issues = json.loads(gh("issue", "list", "-R", REPO, "--label", "proposal", "--state", "open",
                           "--json", "number,title,body,labels"))
    cu = colab_cu()
    approved = False
    for it in issues:
        labels = {l["name"] for l in it["labels"]}
        if labels & {"approved", "needs-human"}:
            continue
        n = str(it["number"])
        bad = problems(it, cu)
        if bad:
            subprocess.run(["gh", "label", "create", "needs-human", "-R", REPO, "--color", "d93f0b"],
                           capture_output=True)
            gh("issue", "edit", n, "-R", REPO, "--add-label", "needs-human")
            gh("issue", "comment", n, "-R", REPO, "--body",
               "**자동 승인 보류** @sooyahh 확인 필요\n" + "\n".join(f"- {b}" for b in bad)
               + "\n\n문제가 없으면 `approved` 라벨을 직접 달아 주세요.")
            print(f"#{n}: needs-human {bad}")
        else:
            gh("issue", "edit", n, "-R", REPO, "--add-label", "approved")
            gh("issue", "comment", n, "-R", REPO, "--body",
               f"**자동 승인** ({'/'.join(CFG.get('gpu_cu_per_hour', {}) or ['T4', 'none'])}, 예산 ≤ {CFG['default_budget_hours']}h, 공식 Val 미사용, "
               f"Colab 잔량 {cu['units_left']:.1f} CU, 신규 ID). Codex 구현을 시작합니다.")
            print(f"#{n}: approved")
            approved = True
    if approved:
        gh("workflow", "run", "commander.yml", "-R", REPO, "--ref", "main")


if __name__ == "__main__":
    main()
