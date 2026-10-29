"""Check workflow links and, optionally, a running ComfyUI server without generation."""

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_NODES = {"SetNode", "GetNode", "Note", "MarkdownNote", "Reroute", "Label (rgthree)",
                  "Fast Groups Bypasser (rgthree)", "Fast Groups Muter (rgthree)", "忽略多组孤海"}


def check_workflow(path: Path, object_info: dict[str, Any] | None = None) -> None:
    workflow = json.loads(path.read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in workflow["nodes"]}
    if len(nodes) != len(workflow["nodes"]):
        raise ValueError(f"Duplicate node IDs: {path.name}")
    links = {link[0]: link for link in workflow["links"]}
    if len(links) != len(workflow["links"]):
        raise ValueError(f"Duplicate link IDs: {path.name}")
    for link_id, source_id, source_slot, target_id, target_slot, _ in links.values():
        source, target = nodes[source_id], nodes[target_id]
        if target["inputs"][target_slot]["link"] != link_id:
            raise ValueError(f"Broken input link {link_id}: {path.name}")
        if link_id not in (source["outputs"][source_slot].get("links") or []):
            raise ValueError(f"Broken output link {link_id}: {path.name}")
    if object_info is not None:
        missing = {node["type"] for node in nodes.values()} - object_info.keys() - FRONTEND_NODES
        if missing:
            raise ValueError(f"Missing backend nodes in {path.name}: {sorted(missing)}")
    print(f"OK {path.name}: {len(nodes)} nodes, {len(links)} links")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="For example http://127.0.0.1:8188")
    parser.add_argument("--include-original", action="store_true")
    arguments = parser.parse_args()
    object_info = None
    if arguments.url:
        with urlopen(arguments.url.rstrip("/") + "/object_info", timeout=30) as response:
            object_info = json.load(response)
        options = object_info["BasicScheduler"]["input"]["required"]["scheduler"][1]["options"]
        if "beta57" not in options:
            raise ValueError("beta57 is missing: install RES4LYF and restart ComfyUI")
    for path in sorted((ROOT / "workflows").glob("*.json")):
        if path.name.startswith("AIHUB-") and not arguments.include_original:
            continue
        check_workflow(path, object_info)
    print("Checks passed. No generation was queued; model availability is a separate check.")


if __name__ == "__main__":
    main()
