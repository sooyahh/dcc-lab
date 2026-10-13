"""Runner fixes for M2-SSL-005 Drive deaths. Run: python3 runner/test_runtime_io.py"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import drive_io
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


class PythonPathTests(unittest.TestCase):
    def test_command_assignment_keeps_runner_dir(self) -> None:
        cmd = 'PYTHONPATH=src python scripts/lab/m2-ssl-005.py --output "$LAB_OUT" --epochs 15'
        got = lab_runner.inject_runner_on_pythonpath(cmd, "/content/dcc-lab/runner")
        self.assertTrue(got.startswith("PYTHONPATH=/content/dcc-lab/runner:src python "))
        quoted = lab_runner.inject_runner_on_pythonpath(
            'env PYTHONPATH="src:extra" python train.py', "/opt/runner")
        self.assertIn('PYTHONPATH="/opt/runner:src:extra"', quoted)
        plain = "python scripts/lab/m2-ssl-005.py"
        self.assertEqual(lab_runner.inject_runner_on_pythonpath(plain, "/opt/runner"), plain)

    def test_injected_pythonpath_loads_sitecustomize(self) -> None:
        runner = str(Path(drive_io.__file__).resolve().parent)
        # The production failure: the job command assigns PYTHONPATH=src and drops the runner dir.
        cmd = lab_runner.inject_runner_on_pythonpath(
            f'PYTHONPATH=src {sys.executable} -c "import drive_io; print(drive_io._INSTALLED)"', runner)
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        got = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
        self.assertIn("True", got.stdout, got.stderr)
        bare = subprocess.run(
            f'PYTHONPATH=src {sys.executable} -c "import drive_io"',
            shell=True, capture_output=True, text=True, env=env,
        )
        self.assertNotEqual(bare.returncode, 0)


class DriveCopyTests(unittest.TestCase):
    def test_chunked_copy_matches_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "ckpt_last.pt"
            payload = bytes(i % 251 for i in range(100_000))
            src.write_bytes(payload)
            dst = root / "drv" / "ckpt_last.pt.tmp"
            dst.parent.mkdir()
            drive_io.copy_onto_drive(src, dst, chunk=16_384, chunk_timeout=10, attempts=1)
            self.assertEqual(dst.read_bytes(), payload)

    def test_timeout_kills_worker_and_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "ckpt_last.pt"
            src.write_bytes(b"x" * 1000)
            pidfile = root / "pid"
            dst = root / "drv" / "ckpt_last.pt.tmp"
            dst.parent.mkdir()
            saved = drive_io._COPY_WORKER_SRC
            drive_io._COPY_WORKER_SRC = (
                "import os, time, sys\n"
                f"open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
                "time.sleep(60)\n"
            )
            try:
                t0 = time.monotonic()
                with self.assertRaises(OSError):
                    drive_io.copy_onto_drive(src, dst, chunk_timeout=0.4, attempts=1)
                self.assertLess(time.monotonic() - t0, 5)
                pid = int(pidfile.read_text())
                gone = False
                for _ in range(40):
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        gone = True
                        break
                    time.sleep(0.05)
                self.assertTrue(gone)
            finally:
                drive_io._COPY_WORKER_SRC = saved

    def test_install_copies_large_drive_file_and_replaces(self) -> None:
        saved = (shutil.copyfile, os.replace, os.rename, drive_io._INSTALLED)
        env_saved = os.environ.get("LAB_DRIVE_MARK"), os.environ.get("LAB_DRIVE_COPY_MIN")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                mark = root / "drv"
                mark.mkdir()
                os.environ["LAB_DRIVE_MARK"] = str(mark)
                os.environ["LAB_DRIVE_COPY_MIN"] = "10"
                drive_io._INSTALLED = False
                drive_io.install()
                src = root / "local.pt"
                src.write_bytes(b"abc" * 20)
                dst = mark / "ckpt_last.pt.tmp"
                self.assertEqual(shutil.copyfile(src, dst), dst)
                self.assertEqual(dst.read_bytes(), src.read_bytes())
                final = mark / "ckpt_last.pt"
                os.replace(dst, final)
                self.assertFalse(dst.exists())
                self.assertEqual(final.read_bytes(), src.read_bytes())
                small_src = root / "small.txt"
                small_dst = mark / "small.txt"
                small_src.write_bytes(b"z")
                shutil.copyfile(small_src, small_dst)
                self.assertEqual(small_dst.read_bytes(), b"z")
        finally:
            shutil.copyfile, os.replace, os.rename, drive_io._INSTALLED = saved
            for key, val in zip(("LAB_DRIVE_MARK", "LAB_DRIVE_COPY_MIN"), env_saved):
                if val is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = val

    def test_publish_and_ckpt_age(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exp = root / "M2-SSL-005"
            exp.mkdir()
            self.assertIsNone(drive_io.ckpt_age_min(exp, timeout=10))
            (exp / "ckpt_last.pt").write_bytes(b"ckpt")
            age = drive_io.ckpt_age_min(exp, timeout=10)
            self.assertIsNotNone(age)
            assert age is not None
            self.assertLess(age, 1)
            status = root / "status"
            ok = drive_io.publish_status(status, {"heartbeat.json": '{"a": 1}\n'},
                                         "resources_colab-a.jsonl", '{"a": 1}\n', timeout=10)
            self.assertTrue(ok)
            self.assertIn('"a": 1', (status / "heartbeat.json").read_text())
            self.assertTrue((status / "resources_colab-a.jsonl").read_text().endswith("\n"))

    def test_append_timeout_unblocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / "local.log"
            local.write_bytes(b"hello\n")
            fifo = root / "run.log"
            os.mkfifo(fifo)
            t0 = time.monotonic()
            with self.assertRaises(TimeoutError):
                drive_io.append_file(local, fifo, 0, timeout=0.4)
            self.assertLess(time.monotonic() - t0, 5)

    def test_run_timeout(self) -> None:
        t0 = time.monotonic()
        with self.assertRaises(TimeoutError):
            drive_io._run("import time; time.sleep(30)", 0.3)
        self.assertLess(time.monotonic() - t0, 5)

    def test_wedged_helper_fails_fast(self) -> None:
        class _Stuck:
            def poll(self) -> None:
                return None

        saved = drive_io._wedged
        drive_io._wedged = _Stuck()  # type: ignore[assignment]
        try:
            t0 = time.monotonic()
            with self.assertRaises(TimeoutError):
                drive_io._run("print(1)", 5)
            self.assertLess(time.monotonic() - t0, 1)
        finally:
            drive_io._wedged = saved


def _restore_env(saved: dict[str, str | None]) -> None:
    for key, val in saved.items():
        if val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = val


class DriveResumeTests(unittest.TestCase):
    def test_partial_resume_keeps_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = bytes(i % 251 for i in range(80_000))
            src = root / "zip.bin"
            src.write_bytes(payload)
            dst = root / "zip.bin.tmp"
            dst.write_bytes(payload[:30_000])
            drive_io.copy_onto_drive(src, dst, chunk=8_000, chunk_timeout=10, attempts=2)
            self.assertEqual(dst.read_bytes(), payload)

    def test_complete_dest_does_not_recopy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = bytes(i % 251 for i in range(4_000))
            src = root / "zip.bin"
            src.write_bytes(payload)
            dst = root / "zip.bin.tmp"
            dst.write_bytes(payload)
            calls: list[int] = []
            real = drive_io._popen

            def wrapped(code: str):
                calls.append(1)
                return real(code)

            drive_io._popen = wrapped
            try:
                drive_io.copy_onto_drive(src, dst, chunk=1_000, chunk_timeout=10, attempts=1)
            finally:
                drive_io._popen = real
            self.assertEqual(calls, [])
            self.assertEqual(dst.read_bytes(), payload)

    def test_timeout_keeps_partial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "zip.bin"
            src.write_bytes(b"x" * 1000)
            dst = root / "zip.bin.tmp"
            dst.write_bytes(b"hello-partial")
            saved = drive_io._COPY_WORKER_SRC
            drive_io._COPY_WORKER_SRC = "import time\ntime.sleep(60)\n"
            try:
                with self.assertRaises(OSError):
                    drive_io.copy_onto_drive(src, dst, chunk_timeout=0.4, attempts=1)
                self.assertEqual(dst.read_bytes(), b"hello-partial")
            finally:
                drive_io._COPY_WORKER_SRC = saved

    def test_drive_read_reopens_each_span(self) -> None:
        keys = ("LAB_DRIVE_MARK", "LAB_DRIVE_SPAN_BYTES", "LAB_WORK", "LAB_DRIVE_CACHE_MIN")
        saved = {key: os.environ.get(key) for key in keys}
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                mark = root / "drv"
                mark.mkdir()
                os.environ["LAB_DRIVE_MARK"] = str(mark)
                os.environ["LAB_DRIVE_SPAN_BYTES"] = "20000"
                os.environ.pop("LAB_WORK", None)
                payload = bytes(i % 251 for i in range(50_000))
                src = mark / "TS.zip"
                src.write_bytes(payload)
                dst = root / "TS.zip.tmp"
                calls: list[int] = []
                real = drive_io._popen

                def wrapped(code: str):
                    calls.append(1)
                    return real(code)

                drive_io._popen = wrapped
                try:
                    drive_io.copy_onto_drive(src, dst, chunk=8_000, chunk_timeout=10, attempts=2)
                finally:
                    drive_io._popen = real
                self.assertGreaterEqual(len(calls), 3)
                self.assertEqual(dst.read_bytes(), payload)
        finally:
            _restore_env(saved)

    def test_cache_hit_ignores_later_source_bytes(self) -> None:
        keys = ("LAB_DRIVE_MARK", "LAB_WORK", "LAB_DRIVE_CACHE_MIN", "LAB_DRIVE_SPAN_BYTES")
        saved = {key: os.environ.get(key) for key in keys}
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                mark = root / "drv"
                mark.mkdir()
                work = root / "lab_work" / "M2-SSL-005"
                work.mkdir(parents=True)
                os.environ["LAB_DRIVE_MARK"] = str(mark)
                os.environ["LAB_WORK"] = str(work)
                os.environ["LAB_DRIVE_CACHE_MIN"] = "10"
                os.environ["LAB_DRIVE_SPAN_BYTES"] = "1000000"
                payload = bytes(i % 251 for i in range(50_000))
                src = mark / "TS.zip"
                src.write_bytes(payload)
                dst = work / "TS.zip.tmp"
                drive_io.copy_onto_drive(src, dst, chunk=8_000, chunk_timeout=10, attempts=2)
                cache = root / "lab_work" / "_drive_cache" / f"TS.zip.{len(payload)}"
                self.assertTrue(cache.is_file())
                self.assertEqual(cache.stat().st_ino, dst.stat().st_ino)
                src.write_bytes(bytes((i + 3) % 251 for i in range(len(payload))))
                dst2 = work / "again.tmp"
                drive_io.copy_onto_drive(src, dst2, chunk=8_000, chunk_timeout=10, attempts=2)
                self.assertEqual(dst2.read_bytes(), payload)
        finally:
            _restore_env(saved)


class ClaimTests(unittest.TestCase):
    def test_single_slot_adopts_the_other_notebook(self) -> None:
        self.assertTrue(lab_runner.adopts_running("colab-b", "colab-a", 1))
        self.assertTrue(lab_runner.adopts_running("colab-a", "colab-b", 1))
        self.assertTrue(lab_runner.adopts_running("colab-b", "colab-b", 1))
        self.assertFalse(lab_runner.adopts_running("colab-b", "colab-a", 2))
        self.assertTrue(lab_runner.adopts_running("colab-b", "colab-b", 2))
        self.assertTrue(lab_runner.adopts_running("colab-a", None, 2))
        self.assertFalse(lab_runner.adopts_running("colab-b", None, 2))


class TorchHookTests(unittest.TestCase):
    def test_torch_module_safe_open_is_redirected(self) -> None:
        mod = types.ModuleType("safetensors.torch")
        seen: dict[str, str] = {}

        def original(filename, *args, **kwargs):
            seen["filename"] = filename
            return "handle"

        mod.safe_open = original
        real = safetensors_local.localize_safetensors
        safetensors_local.localize_safetensors = (
            lambda filename, drive_mark="/content/drive": "/local/model.safetensors"
            if "drive" in str(filename) else None
        )
        try:
            safetensors_local._patch_torch_module(mod)
            self.assertEqual(mod.safe_open("/content/drive/m/model.safetensors", framework="pt"), "handle")
            self.assertEqual(seen["filename"], "/local/model.safetensors")
            self.assertTrue(mod._runner_safe_open)
        finally:
            safetensors_local.localize_safetensors = real


if __name__ == "__main__":
    unittest.main()
