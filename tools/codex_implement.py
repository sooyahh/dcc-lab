"""Run the Codex implementer inside GitHub Actions (no LLM tokens of Claude are used here).

Reads WORK (json list from commander_check.py) from argv[1] or env WORK, handles:
  implement {"issue": N, "exp": EXP}  dcc-lab issue (approved spec) -> team branch sooyah/lab-<exp> -> codex exec
                                       -> commit/push -> team PR "exp(<EXP>): ..." (body ends with COMMAND: ...)
  fix       {"pr": N, "exp": EXP}     team PR labeled lab-fix -> codex exec with the latest review -> push to the PR branch
Prints the remaining WORK (other kinds) as `rest=<json>` to $GITHUB_OUTPUT for the Claude step.

Env: GH_TOKEN (dcc-lab), TEAM_GH_TOKEN (team repo), TEAM_REPO_DIR (team checkout), CODEX_SANDBOX (default workspace-write).
Tokens are removed from the environment codex runs in.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
TEAM = Path(os.environ.get("TEAM_REPO_DIR", "team")).resolve()
TEAM_REPO = json.loads((LAB / "config.json").read_text(encoding="utf-8"))["team_repo"]
STATE = LAB / "state" / "processed.json"
SECRET_ENV = ("GH_TOKEN", "TEAM_GH_TOKEN", "GITHUB_TOKEN", "ACTIONS_RUNTIME_TOKEN", "CODEX_AUTH_JSON")


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None, check: bool = True) -> str:
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:4])} failed: {p.stderr[-1500:]}")
    return p.stdout


def gh_team(*args: str) -> str:
    return run(["gh", *args], env={**os.environ, "GH_TOKEN": os.environ["TEAM_GH_TOKEN"]})


def codex(prompt: str, log: Path) -> str:
    env = {k: v for k, v in os.environ.items() if k not in SECRET_ENV}
    sandbox = os.environ.get("CODEX_SANDBOX", "workspace-write")
    p = subprocess.run(["codex", "exec", "-s", sandbox, "-C", str(TEAM), "-o", str(log), "-"],
                       input=prompt, text=True, env=env, capture_output=True)
    print(p.stdout[-4000:])
    if p.returncode != 0:
        raise RuntimeError(f"codex exec failed: {p.stderr[-2000:]}")
    return log.read_text(encoding="utf-8") if log.exists() else ""


def command_line(text: str) -> str:
    lines = [l.strip().strip("`") for l in text.splitlines() if l.strip().strip("`").startswith("COMMAND:")]
    return lines[-1].split("COMMAND:", 1)[1].strip() if lines else ""


def guide() -> str:
    return (LAB / "docs" / "implementer.md").read_text(encoding="utf-8") + (
        "\n\n## 이번 실행 환경\n- 현재 디렉터리가 팀 저장소 루트이고, 브랜치는 이미 준비되어 있다. git 커밋·push·PR은 하지 말고 파일만 수정한다\n"
        "- 마지막 메시지: 변경 파일 목록과 한 줄 요약, 그리고 마지막 줄에 정확히 `COMMAND: <저장소 루트에서 실행할 명령>`\n")


def implement(item: dict, state: dict) -> None:
    body = run(["gh", "issue", "view", str(item["issue"]), "--json", "body", "-q", ".body"])
    m = re.search(r"```json\s*(\{.*?\})\s*```", body, re.S)
    if not m:
        raise RuntimeError(f"issue #{item['issue']}: 명세 JSON 블록 없음")
    spec = json.loads(m.group(1))
    exp = spec["exp_id"]
    branch = f"sooyah/lab-{exp.lower()}"
    log = LAB / "reviews" / f"{exp}.implement.log.md"
    run(["git", "fetch", "-q", "origin", "main"], cwd=TEAM)
    if run(["git", "ls-remote", "--heads", "origin", branch], cwd=TEAM).strip() and log.exists():
        out = log.read_text(encoding="utf-8")             # pushed by an earlier run that failed later: reuse it
        print(f"{exp}: reuse existing branch {branch}")
    else:
        run(["git", "checkout", "-q", "-B", branch, "origin/main"], cwd=TEAM)
        out = codex(f"{guide()}\n\n## 명세\n```json\n{json.dumps(spec, ensure_ascii=False, indent=2)}\n```\n", log)
        if not run(["git", "status", "--porcelain"], cwd=TEAM).strip():
            raise RuntimeError(f"{exp}: codex가 파일을 바꾸지 않음")
        run(["git", "add", "-A"], cwd=TEAM)
        run(["git", "-c", "user.name=dcc-lab-commander", "-c", "user.email=dcc-lab@users.noreply.github.com",
             "commit", "-q", "-m", f"exp({exp}): {spec['title']}"], cwd=TEAM)
        run(["git", "push", "-q", "-f", "origin", branch], cwd=TEAM)
    cmd = command_line(out)
    pr_body = (f"자동 구현 (Codex) — 명세: sooyahh/dcc-lab#{item['issue']}\n\n"
               f"```json\n{json.dumps(spec, ensure_ascii=False, indent=2)}\n```\n\n"
               f"<details><summary>Codex 요약</summary>\n\n{out[-3000:]}\n</details>\n\nCOMMAND: {cmd}")
    url = gh_team("pr", "create", "-R", TEAM_REPO, "--base", "main", "--head", branch,
                  "--title", f"exp({exp}): {spec['title']}"[:240], "--body", pr_body).strip()
    spec.update(branch=branch, commit="", command=cmd)
    (LAB / "specs").mkdir(exist_ok=True)
    (LAB / "specs" / f"{exp}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    run(["gh", "issue", "comment", str(item["issue"]), "--body", f"Codex 구현 PR: {url}"])
    state.setdefault("implemented_issues", []).append(item["issue"])
    print(f"{exp}: PR {url}")


def fix(item: dict, state: dict) -> None:
    pr = json.loads(gh_team("pr", "view", str(item["pr"]), "-R", TEAM_REPO, "--json", "headRefName,title,body"))
    exp = pr["title"].split("(", 1)[1].split(")", 1)[0]
    reviews = sorted((LAB / "reviews").glob(f"{exp}_*.md"), key=lambda p: p.stat().st_mtime)
    reviews = [r for r in reviews if not r.name.endswith((".implement.log.md", "_verdict.md"))]
    review = reviews[-1].read_text(encoding="utf-8") if reviews else "(검토 파일 없음: PR 댓글 참고)"
    run(["git", "fetch", "-q", "origin", pr["headRefName"]], cwd=TEAM)
    run(["git", "checkout", "-q", "-B", pr["headRefName"], f"origin/{pr['headRefName']}"], cwd=TEAM)
    log = LAB / "reviews" / f"{exp}.fix.log.md"
    out = codex(f"{guide()}\n\n## 원래 PR 본문(명세 포함)\n{pr['body'][:8000]}\n\n"
                f"## 검토에서 지적된 문제 (BLOCKER/MAJOR 모두 해결)\n{review}\n", log)
    if run(["git", "status", "--porcelain"], cwd=TEAM).strip():
        run(["git", "add", "-A"], cwd=TEAM)
        run(["git", "-c", "user.name=dcc-lab-commander", "-c", "user.email=dcc-lab@users.noreply.github.com",
             "commit", "-q", "-m", f"exp({exp}): fix per review"], cwd=TEAM)
        run(["git", "push", "-q", "origin", pr["headRefName"]], cwd=TEAM)
    cmd = command_line(out)
    if cmd:
        spec_p = LAB / "specs" / f"{exp}.json"
        if spec_p.exists():
            spec = json.loads(spec_p.read_text(encoding="utf-8"))
            spec["command"] = cmd
            spec_p.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    gh_team("pr", "edit", str(item["pr"]), "-R", TEAM_REPO, "--remove-label", "lab-fix")
    gh_team("pr", "comment", str(item["pr"]), "-R", TEAM_REPO, "--body", "Codex가 검토 지적 사항을 반영해 커밋했습니다. 다음 사령탑 실행에서 재검토합니다.")
    print(f"{exp}: fixed PR #{item['pr']}")


def main() -> None:
    work = json.loads(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("WORK", "[]"))
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    rest, errors = [], []
    for item in work:
        try:
            if item["kind"] == "implement":
                implement(item, state)
            elif item["kind"] == "fix":
                fix(item, state)
            else:
                rest.append(item)
        except Exception as exc:                                  # report to Claude instead of failing the run
            errors.append({"kind": "report", "about": item, "error": str(exc)[-1500:]})
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    rest += errors
    print("rest:", json.dumps(rest, ensure_ascii=False))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"rest={json.dumps(rest, ensure_ascii=False)}\n")


if __name__ == "__main__":
    main()
