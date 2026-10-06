"""Smoke job: checks GPU, team-repo import path and official data root. Writes $LAB_OUT/metrics.json."""
import json
import os

cuda, gpu = None, None
try:
    import torch
    cuda = torch.cuda.is_available()
    gpu = torch.cuda.get_device_name(0) if cuda else None
except ImportError:
    pass
try:
    from dcc_data.colab_env import find_data_root
    root = find_data_root()
    data = {"data_root": str(root), "training_entries": len(list((root / "Training").iterdir()))}
except Exception as exc:
    data = {"data_root": f"ERR {type(exc).__name__}: {str(exc)[:300]}"}
m = {"exp_id": os.environ["LAB_EXP_ID"], "seed": 0,
     "primary_metric": {"name": "smoke", "value": 1.0, "split": "internal_holdout"},
     "metrics": {"cuda": cuda, "gpu": gpu, **data}}
print(m)
with open(os.path.join(os.environ["LAB_OUT"], "metrics.json"), "w", encoding="utf-8") as f:
    json.dump(m, f, ensure_ascii=False)

# Drive layout diagnostics (names only, depth-limited) to locate the official data folder
from pathlib import Path
drive = Path("/content/drive")
diag = {}
for base in (drive, drive / "MyDrive", drive / ".shortcut-targets-by-id"):
    try:
        diag[str(base)] = sorted(p.name for p in base.iterdir())[:60]
    except Exception as exc:
        diag[str(base)] = f"ERR {type(exc).__name__}"
sc = drive / ".shortcut-targets-by-id"
if sc.is_dir():
    for d in sorted(sc.iterdir())[:20]:
        try:
            diag[str(d)] = sorted(p.name for p in d.iterdir())[:20]
        except Exception as exc:
            diag[str(d)] = f"ERR {type(exc).__name__}"
m["drive_diag"] = diag
print(diag)
with open(os.path.join(os.environ["LAB_OUT"], "metrics.json"), "w", encoding="utf-8") as f:
    json.dump(m, f, ensure_ascii=False)
