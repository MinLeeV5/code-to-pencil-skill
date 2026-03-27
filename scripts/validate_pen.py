#!/usr/bin/env python3
"""
Minimal validator for generated Pencil files.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import sys
from pathlib import Path


def fail(message: str) -> int:
    print(f"[FAIL] {message}")
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a generated .pen file.")
    parser.add_argument("pen", help="Path to the .pen file")
    parser.add_argument("--require-frame", action="append", default=[], help="Required top-level frame names")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pen_path = Path(args.pen).resolve()

    if not pen_path.exists():
        return fail(f"{pen_path} does not exist")

    try:
        data = json.loads(pen_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return fail(f"Invalid JSON: {exc}")

    if "children" not in data or not isinstance(data["children"], list):
        return fail("Top-level `children` array is missing")

    top_frames = [child for child in data["children"] if isinstance(child, dict) and child.get("type") == "frame"]
    names = [frame.get("name", "") for frame in top_frames]

    duplicate_names = [name for name, count in Counter(name for name in names if name).items() if count > 1]
    if duplicate_names:
        return fail(f"Duplicate top-level frame name(s): {', '.join(duplicate_names)}")

    missing = [name for name in args.require_frame if name not in names]
    if missing:
        return fail(f"Missing required top-level frame(s): {', '.join(missing)}")

    context_missing = [frame.get("id", "<unknown>") for frame in top_frames if not frame.get("context")]
    if context_missing:
        return fail(f"Top-level frame(s) missing `context`: {', '.join(context_missing)}")

    resource_errors: list[str] = []

    def walk(node: dict) -> None:
        fill = node.get("fill")
        if isinstance(fill, dict) and fill.get("type") == "image":
            url = fill.get("url", "")
            if url.startswith("./") or url.startswith("../"):
                asset_path = (pen_path.parent / url).resolve()
                if not asset_path.exists():
                    resource_errors.append(f"{node.get('id', '<unknown>')} -> missing asset {url}")
        for child in node.get("children", []) or []:
            if isinstance(child, dict):
                walk(child)

    for frame in top_frames:
        walk(frame)

    if resource_errors:
        return fail("; ".join(resource_errors))

    print("[OK] JSON is readable")
    print(f"[OK] top-level frames: {', '.join(names) if names else '<none>'}")
    print("[OK] top-level context present")
    print("[OK] referenced relative assets exist")
    return 0


if __name__ == "__main__":
    sys.exit(main())
