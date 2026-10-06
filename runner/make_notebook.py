"""Regenerate runner/lab_worker.ipynb (copy it to Drive dcc_lab/ after changes)."""
import json
from pathlib import Path

SETUP = """import os, pathlib, subprocess
sec = pathlib.Path('/content/drive/MyDrive/dcc_lab/.secrets')
tok = (sec / 'github_token.txt').read_text().strip()          # sooyahh/dcc-lab read/write
assert (sec / 'github_team_token.txt').exists(), 'github_team_token.txt 없음'
repo = pathlib.Path('/content/dcc-lab')
if not (repo / '.git').exists():
    subprocess.run(['git', 'clone', '-q', f'https://x-access-token:{tok}@github.com/sooyahh/dcc-lab.git', str(repo)], check=True)
subprocess.run(['git', '-C', str(repo), 'fetch', '-q', 'origin', 'main'], check=True)
subprocess.run(['git', '-C', str(repo), 'reset', '-q', '--hard', 'origin/main'], check=True)
print('dcc-lab', subprocess.run(['git', '-C', str(repo), 'log', '-1', '--format=%h %s'],
                                capture_output=True, text=True).stdout)"""


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text}


nb = {
    "nbformat": 4, "nbformat_minor": 5,
    "metadata": {"accelerator": "GPU", "colab": {"provenance": []},
                 "kernelspec": {"name": "python3", "display_name": "Python 3"}},
    "cells": [
        md("# DCC lab worker\n\n"
           "런타임 유형 GPU(T4 기본) → **모두 실행**. 큐가 10분 비면 런타임까지 스스로 해제합니다(컴퓨팅 단위 절약).\n"
           "끊겨도 다시 '모두 실행'하면 진행 중이던 실험을 이어서 재개합니다. 이 노트북은 수정하지 마세요."),
        code("from google.colab import drive\ndrive.mount('/content/drive')\n"
             "!nvidia-smi --query-gpu=name,memory.total --format=csv"),
        code(SETUP),
        code("!python /content/dcc-lab/runner/lab_runner.py --idle-exit-min 10 --unassign-on-idle"),
    ],
}
out = Path(__file__).with_name("lab_worker.ipynb")
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(out)
