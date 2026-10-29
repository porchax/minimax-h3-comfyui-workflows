"""Run ComfyUI in the foreground, bound to localhost for SSH forwarding."""

import argparse
from pathlib import Path
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comfy-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path)
    parser.add_argument("--port", type=int, default=8188)
    arguments = parser.parse_args()
    if not 1 <= arguments.port <= 65535:
        parser.error("Port must be between 1 and 65535")
    directory = arguments.comfy_dir.expanduser().resolve()
    python = arguments.python.expanduser().resolve() if arguments.python else (
        directory / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    )
    subprocess.run([str(python), str(directory / "main.py"), "--listen", "127.0.0.1",
                    "--port", str(arguments.port), "--disable-auto-launch"], cwd=directory, check=True)


if __name__ == "__main__":
    main()
