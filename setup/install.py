"""Install the recorded ComfyUI revision, node packs, workflows and H3 weights."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def read_config(name: str) -> Any:
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))


def run(arguments: list[str]) -> None:
    print("+ " + " ".join(arguments), flush=True)
    subprocess.run(arguments, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_target(models_directory: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    windows_path = PureWindowsPath(relative)
    if (path.is_absolute() or windows_path.is_absolute() or windows_path.drive
            or ".." in path.parts or ".." in windows_path.parts
            or "\\" in relative or not path.parts):
        raise ValueError(f"Invalid model destination: {relative}")
    return models_directory.joinpath(*path.parts)


def verify_model(path: Path, entry: dict[str, Any]) -> None:
    if not path.is_file() or path.stat().st_size != entry["bytes"]:
        raise ValueError(f"Missing model or wrong file size: {path}")
    if sha256(path) != entry["sha256"]:
        raise ValueError(f"SHA256 does not match the recorded model: {path}")
    print(f"SHA256 OK: {path.name}", flush=True)


def download_model(comfy_directory: Path, entry: dict[str, Any]) -> None:
    destination = model_target(comfy_directory / "models", entry["target"])
    if destination.exists():
        verify_model(destination, entry)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    url = (f"https://huggingface.co/{entry['repository']}/resolve/"
           f"{entry['revision']}/{entry['remote_path']}")
    if shutil.which("aria2c"):
        command = ["aria2c", "--continue=true", "--max-tries=8", "--retry-wait=3",
                   "--max-connection-per-server=8", "--split=8", "--file-allocation=none",
                   "--auto-file-renaming=false", "--summary-interval=30",
                   "--dir", str(partial.parent), "--out", partial.name, url]
    else:
        command = ["curl", "--fail", "--location", "--retry", "5", "--continue-at", "-",
                   "--output", str(partial), url]
    run(command)
    verify_model(partial, entry)
    partial.rename(destination)


def checkout_repository(destination: Path, entry: dict[str, Any]) -> None:
    revision = entry["revision"]
    if destination.exists():
        if not (destination / ".git").exists():
            raise ValueError(f"Directory is not a Git checkout: {destination}")
        actual = subprocess.check_output(
            ["git", "-C", str(destination), "rev-parse", "HEAD"], text=True,
        ).strip()
        if actual != revision:
            raise ValueError(
                f"{destination} is at {actual}, expected {revision}. "
                "Use a new directory; existing checkouts are not overwritten."
            )
        if subprocess.check_output(
            ["git", "-C", str(destination), "status", "--porcelain"], text=True,
        ).strip():
            raise ValueError(f"Checkout has local changes: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = ["git", "clone", "--depth", "1", "--filter=blob:none"]
    if entry.get("sparse_exclude"):
        command.append("--sparse")
    run([*command, entry["repository"], str(destination)])
    run(["git", "-C", str(destination), "fetch", "--depth", "1", "origin", revision])
    run(["git", "-C", str(destination), "checkout", "--detach", revision])
    if entry.get("sparse_exclude"):
        patterns = ["/*", *[f"!/{name}/" for name in entry["sparse_exclude"]]]
        run(["git", "-C", str(destination), "sparse-checkout", "set", "--no-cone", *patterns])


def install_packages(python: Path, arguments: list[str]) -> None:
    if shutil.which("uv"):
        run(["uv", "pip", "install", "--python", str(python), *arguments])
    else:
        run([str(python), "-m", "pip", "install", *arguments])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comfy-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path, help="Existing ComfyUI Python; otherwise create .venv")
    parser.add_argument("--profile", choices=["tested", "full"], default="full")
    parser.add_argument("--skip-models", action="store_true")
    parser.add_argument("--skip-dependencies", action="store_true")
    parser.add_argument("--verify-models", action="store_true", help="Only verify model hashes")
    parser.add_argument("--only-model", help="Limit model operations to one filename")
    parser.add_argument("--dry-run", action="store_true", help="Show the plan without writing files")
    arguments = parser.parse_args()
    comfy_directory = arguments.comfy_dir.expanduser().resolve()
    repositories = read_config("repositories.json")
    nodes = [entry for entry in repositories["custom_nodes"] if arguments.profile in entry["profiles"]]
    models = read_config("models.json")
    if arguments.only_model:
        models = [entry for entry in models if Path(entry["target"]).name == arguments.only_model]
        if not models:
            parser.error("Unknown --only-model filename")
    if arguments.dry_run:
        print(json.dumps({"comfy_directory": str(comfy_directory), "profile": arguments.profile,
                          "comfyui_revision": repositories["comfyui"]["revision"],
                          "nodes": [entry["name"] for entry in nodes],
                          "models": [entry["target"] for entry in models],
                          "model_bytes": sum(entry["bytes"] for entry in models),
                          "skip_dependencies": arguments.skip_dependencies,
                          "skip_models": arguments.skip_models}, indent=2))
        return
    if arguments.verify_models:
        for entry in models:
            verify_model(model_target(comfy_directory / "models", entry["target"]), entry)
        return
    checkout_repository(comfy_directory, repositories["comfyui"])
    for entry in nodes:
        checkout_repository(comfy_directory / "custom_nodes" / entry["name"], entry)
    if not arguments.skip_dependencies:
        python = arguments.python.expanduser().resolve() if arguments.python else (
            comfy_directory / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        )
        if not python.exists():
            if arguments.python:
                raise FileNotFoundError(python)
            run([sys.executable, "-m", "venv", str(comfy_directory / ".venv")])
        install_packages(python, ["torch==2.10.0", "torchvision==0.25.0", "torchaudio==2.10.0",
                                  "--index-url", "https://download.pytorch.org/whl/cu130"])
        constraints = comfy_directory / "user/h3-portable/torch-constraints.txt"
        constraints.parent.mkdir(parents=True, exist_ok=True)
        constraints.write_text("torch==2.10.0\ntorchvision==0.25.0\ntorchaudio==2.10.0\n")
        requirements = ["-c", str(constraints), "-r", str(comfy_directory / "requirements.txt"),
                        "-r", str(ROOT / "config/runtime-tested.txt")]
        if arguments.profile == "full":
            requirements += ["-r", str(ROOT / "config/runtime-full-extra.txt")]
        install_packages(python, requirements)
    if arguments.profile == "full":
        target = comfy_directory / "custom_nodes/vrgdg_general_utilities"
        source = comfy_directory / "custom_nodes/comfyui-vrgamedevgirl/optional_nodes/general_utilities"
        if not target.exists():
            shutil.copytree(source, target)
    workflow_directory = comfy_directory / "user/default/workflows"
    workflow_directory.mkdir(parents=True, exist_ok=True)
    for workflow in (ROOT / "workflows").glob("*.json"):
        destination = workflow_directory / workflow.name
        if destination.exists() and destination.read_bytes() != workflow.read_bytes():
            raise ValueError(f"Workflow has local changes; not overwriting: {destination}")
        shutil.copyfile(workflow, destination)
    if not arguments.skip_models:
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(lambda entry: download_model(comfy_directory, entry), models))
    print(f"Core, node packs and workflow files installed: {comfy_directory}")
    if arguments.profile == "full":
        print("Additional models for the original workflow are listed in docs/MODELS.md. "
              "Installing node packs alone does not install these models or DLSS runtime.")


if __name__ == "__main__":
    main()
