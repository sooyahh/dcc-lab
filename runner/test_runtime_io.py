"""Runner fixes for M2-SSL-005 Drive safetensors deaths. Run: python3 runner/test_runtime_io.py"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lab_runner
import safetensors_local


class LocalizeTests(unittest.TestCase):
    def test_ignores_local_and_non_safetensors(self) -> None:
        self.assertIsNone(safetensors_local.localize_safetensors("/tmp/model.safetensors", drive_mark="/content/drive"))
        self.assertIsNone(safetensors_local.localize_safetensors("/content/drive/x/config.json"))

    def test_copies_drive_file_once(self) -> None:
        import numpy as np
        from safetensors import safe_open
        from safetensors.numpy import save_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "drive" / "models" / "wav2vec" / "model.safetensors"
            src.parent.mkdir(parents=True)
            save_file({"w": np.arange(8, dtype=np.float32)}, src)
            os.environ["LAB_WORK"] = str(root / "work")
            try:
                first = safetensors_local.localize_safetensors(src, drive_mark=str(root / "drive"))
                second = safetensors_local.localize_safetensors(src, drive_mark=str(root / "drive"))
                self.assertEqual(first, second)
                assert first is not None
                self.assertTrue(first.startswith(str(root / "work")))
                self.assertEqual(Path(first).stat().st_size, src.stat().st_size)
                with safe_open(first, framework="np") as handle:
                    got = handle.get_tensor("w")
                self.assertEqual(list(got), list(range(8)))
            finally:
                os.environ.pop("LAB_WORK", None)


class InstallTests(unittest.TestCase):
    def test_safe_open_reads_local_copy(self) -> None:
        import numpy as np
        import safetensors
        from safetensors.numpy import save_file

        original = safetensors.safe_open
        safetensors_local._INSTALLED = False
        try:
            safetensors_local.install()
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                src = root / "content" / "drive" / "models" / "m" / "model.safetensors"
                src.parent.mkdir(parents=True)
                save_file({"w": np.ones((3,), dtype=np.float32)}, src)
                os.environ["LAB_WORK"] = str(root / "work")
                # production mark is the absolute Drive prefix; point the helper at this temp tree
                real = safetensors_local.localize_safetensors

                def fake(filename, drive_mark="/content/drive"):
                    return real(filename, drive_mark=str(root / "content" / "drive"))

                safetensors_local.localize_safetensors = fake
                try:
                    with safetensors.safe_open(src, framework="np") as handle:
                        self.assertEqual(float(handle.get_tensor("w")[0]), 1.0)
                    copied = list((root / "work" / "_safetensors_local").glob("*.safetensors"))
                    self.assertEqual(len(copied), 1)
                finally:
                    safetensors_local.localize_safetensors = real
                    os.environ.pop("LAB_WORK", None)
        finally:
            safetensors.safe_open = original
            safetensors_local._INSTALLED = False


class MirrorTests(unittest.TestCase):
    def test_appends_only_new_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local, drive = root / "local.log", root / "drive" / "run.log"
            local.write_bytes(b"one\n")
            off = safetensors_local.append_log_mirror(local, drive, 0)
            local.write_bytes(b"one\ntwo\n")
            off = safetensors_local.append_log_mirror(local, drive, off)
            self.assertEqual(drive.read_bytes(), b"one\ntwo\n")
            self.assertEqual(safetensors_local.append_log_mirror(local, drive, off), off)


class EnvTests(unittest.TestCase):
    def test_child_env_strips_tokens_and_disables_xet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, out, work = Path(tmp) / "repo", Path(tmp) / "out", Path(tmp) / "work"
            env = lab_runner.build_child_env(
                repo, "M2-SSL-005", out, work, None,
                {"DCC_LAB_TOKEN": "secret", "DCC_TEAM_TOKEN": "secret2", "PATH": "/usr/bin", "PYTHONPATH": "src"},
            )
        self.assertNotIn("DCC_LAB_TOKEN", env)
        self.assertNotIn("DCC_TEAM_TOKEN", env)
        self.assertEqual(env["HF_HUB_DISABLE_XET"], "1")
        self.assertEqual(env["LAB_EXP_ID"], "M2-SSL-005")
        self.assertTrue(env["PYTHONPATH"].startswith(str(Path(lab_runner.__file__).resolve().parent)))
        self.assertIn(str(repo / "src"), env["PYTHONPATH"])

    def test_describe_ckpt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = lab_runner.describe_ckpt("M2-SSL-005", root)
            self.assertIn("없음", missing)
            ck = root / "M2-SSL-005" / "ckpt_last.pt"
            ck.parent.mkdir()
            ck.write_bytes(b"x" * 100)
            found = lab_runner.describe_ckpt("M2-SSL-005", root)
            self.assertIn("ckpt_last.pt 있음", found)
            self.assertIn(str(ck), found)


if __name__ == "__main__":
    unittest.main()
