"""Checks for transfer safety and the installer's non-destructive behavior."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, filename: str) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, ROOT / "setup" / filename)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Cannot load {filename}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


installer = load_module("h3_install", "install.py")
checker = load_module("h3_check", "check.py")


class PortabilityTests(unittest.TestCase):
    def test_model_paths_cannot_escape_the_model_folder(self) -> None:
        for value in ["../outside", "/tmp/outside", "vae/../../outside"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                installer.model_target(Path("/models"), value)

    def test_existing_corrupt_model_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "models/vae/example.safetensors"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"bad")
            entry = {"target": "vae/example.safetensors", "bytes": 3, "sha256": "0" * 64}
            with patch.object(installer, "run") as command, self.assertRaises(ValueError):
                installer.download_model(root, entry)
            command.assert_not_called()
            self.assertEqual(target.read_bytes(), b"bad")

    def test_dry_run_does_not_create_the_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "new-install"
            completed = subprocess.run(
                [sys.executable, str(ROOT / "setup/install.py"), "--comfy-dir",
                 str(destination), "--dry-run"], check=True, capture_output=True, text=True,
            )
            plan = json.loads(completed.stdout)
            self.assertEqual(plan["profile"], "full")
            self.assertEqual(len(plan["nodes"]), 19)
            self.assertFalse(destination.exists())

    def test_existing_git_checkout_is_not_changed_to_another_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            (destination / ".git").mkdir()
            entry = {"revision": "b" * 40, "repository": "https://github.com/example/example"}
            with patch.object(installer.subprocess, "check_output", return_value="a" * 40), \
                    patch.object(installer, "run") as command, self.assertRaises(ValueError):
                installer.checkout_repository(destination, entry)
            command.assert_not_called()

    def test_workflow_check_detects_a_disconnected_input(self) -> None:
        workflow = json.loads((ROOT / "workflows/H3-PhotoText-5090.json").read_text())
        first_link = workflow["links"][0]
        target = next(node for node in workflow["nodes"] if node["id"] == first_link[3])
        target["inputs"][first_link[4]]["link"] = None
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "broken.json"
            path.write_text(json.dumps(workflow))
            with self.assertRaises(ValueError):
                checker.check_workflow(path)


if __name__ == "__main__":
    unittest.main()
