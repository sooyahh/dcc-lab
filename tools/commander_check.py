"""Token-free pre-check for the cloud commander: decide whether Claude needs to run at all.

Writes `work=<json list>` to $GITHUB_OUTPUT (empty list -> the Claude step is skipped).
Work items:
  {"kind": "judge",     "exp": EXP}              result in done/ or failed/ not yet judged
  {"kind": "implement", "issue": N, "exp": EXP}  dcc-lab issue labeled `approved` (spec proposal), not yet sent to Codex
  {"kind": "review",    "pr": N, "sha": SHA}     open team-repo PR titled `exp(...)` whose head sha was not reviewed yet
  {"kind": "fix",       "pr": N}                 team-repo exp PR labeled lab-fix (review FAIL) -> Codex fixes it
  {"kind": "merge",     "pr": N}                 team-repo lab PR marked adopted / lab-log, not merged yet
  {"kind": "propose"}                            pipeline idle (no open proposal, no exp job/PR in flight) -> new proposal
State: state/processed.json (committed by the commander run).
Tokens: GH_TOKEN = this repo (workflow token), TEAM_GH_TOKEN = team repo (fine-grained PAT).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
CFG = json.loads((LAB / "config.json").read_text(encoding="utf-8"))
STATE = LAB / "state" / "processed.json"
TEAM = CFG["team_repo"]
LAB_REPO = os.environ.get("GITHUB_REPOSITORY", "sooyahh/dcc-lab")


def gh_json(*args: str, team: bool = False) -> list:
    env = dict(os.environ)
    if team and os.environ.get("TEAM_GH_TOKEN"):
        env["GH_TOKEN"] = os.environ["TEAM_GH_TOKEN"]          # fine-grained tokens are per owner
    p = subprocess.run(["gh", *args], capture_output=True, text=True, env=env)
    return json.loads(p.stdout or "[]") if p.returncode == 0 else []


def main() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    judged = set(state.get("judged", []))
    sent = set(map(str, state.get("implemented_issues", [])))
    reviewed = set(state.get("reviewed_shas", []))
    merged = set(map(str, state.get("merged_prs", [])))
    frozen = dt.datetime.now(dt.timezone.utc) > dt.datetime.fromisoformat(CFG["freeze_at"])
    work: list[dict] = []

    for folder in ("done", "failed"):
        for p in sorted((LAB / folder).glob("*.json")):
            rec = json.loads(p.read_text(encoding="utf-8"))
            exp = rec["spec"]["exp_id"]
            key = f"{folder}/{p.name}@{rec.get('finished_at', '')}"   # one judgment per result, not per experiment
            if key not in judged and not exp.startswith(("SMOKE", "INFRA")):   # infra jobs are not experiments
                work.append({"kind": "judge", "exp": exp, "key": key})

    if not frozen:
        for it in gh_json("issue", "list", "-R", LAB_REPO, "--label", "approved", "--state", "open",
                          "--json", "number,title"):
            if str(it["number"]) not in sent:
                work.append({"kind": "implement", "issue": it["number"], "exp": it["title"].split()[0]})
        for pr in gh_json("pr", "list", "-R", TEAM, "--state", "open", "--json", "number,title,headRefOid,labels", team=True):
            labels = {l["name"] for l in pr["labels"]}
            if "lab-log" in labels and str(pr["number"]) not in merged:
                work.append({"kind": "merge", "pr": pr["number"]})       # log-only PR: merge once merge-gate passes
                continue
            if not pr["title"].startswith("exp("):
                continue                                                  # teammates' PRs are never touched
            if "lab-adopted" in labels:
                # already run and judged: new commits here are main merged in (update-branch), never re-review/re-run
                if str(pr["number"]) not in merged:
                    work.append({"kind": "merge", "pr": pr["number"]})
            elif "lab-fix" in labels:
                work.append({"kind": "fix", "pr": pr["number"]})          # Codex fixes per review
            elif pr["headRefOid"] not in reviewed:
                work.append({"kind": "review", "pr": pr["number"], "sha": pr["headRefOid"]})

    # idle pipeline: nothing to judge/build/review and no experiment queued or running -> ask for the next proposal
    if not frozen and not any(w["kind"] in ("judge", "implement", "review", "fix") for w in work):
        in_flight = [p for d in ("queue", "running") for p in (LAB / d).glob("*.json")
                     if not json.loads(p.read_text(encoding="utf-8"))["spec"]["exp_id"].startswith(("SMOKE", "INFRA"))]
        open_exp_prs = [pr for pr in gh_json("pr", "list", "-R", TEAM, "--state", "open", "--json", "title", team=True)
                        if pr["title"].startswith("exp(")]
        proposals = gh_json("issue", "list", "-R", LAB_REPO, "--label", "proposal", "--state", "open", "--json", "number")
        if not in_flight and not open_exp_prs and not proposals:
            work.append({"kind": "propose"})

    print(json.dumps(work, ensure_ascii=False, indent=1))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"work={json.dumps(work, ensure_ascii=False)}\n")


if __name__ == "__main__":
    main()
