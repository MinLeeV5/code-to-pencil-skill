#!/usr/bin/env python3
"""
Build a structured Pencil CLI prompt from page source files.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ASSET_RE = re.compile(r"""import\s+\w+\s+from\s+['"]([^'"]+\.(?:png|svg|jpg|jpeg|webp))['"]""")
DATA_TESTID_RE = re.compile(r"""data-testid(?:=|\s*:\s*)[`'"]([^`'"]+)[`'"]""")
STEP_RE = re.compile(r"""LoginStep\.([A-Z_]+)""")
TEXT_RE = re.compile(r"""(?:content|placeholder|text)\s*[:=]\s*['"]([^'"]{2,80})['"]""")
CLASS_RE = re.compile(r"""className\s*=\s*["'`]([^"'`]+)["'`]""")
HEX_RE = re.compile(r"""#(?:[0-9A-Fa-f]{3,8})""")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def uniq(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def suffix_match_score(import_path: str, candidate_path: str) -> int:
    import_segments = [
        segment for segment in import_path.replace("\\", "/").split("/")
        if segment and not segment.startswith("@")
    ]
    candidate = candidate_path.replace("\\", "/")

    for length in range(len(import_segments), 0, -1):
        suffix = "/".join(import_segments[-length:])
        if candidate.endswith(suffix):
            return length
    return 0


def resolve_asset_path(import_path: str, source_path: Path, repo_root: Path) -> str | None:
    if import_path.startswith(("./", "../")):
        candidate = (source_path.parent / import_path).resolve()
        if candidate.exists():
            return candidate.relative_to(repo_root).as_posix()
        return None

    filename = Path(import_path).name
    if not filename:
        return None

    candidates: list[tuple[int, int, str]] = []
    for candidate in repo_root.rglob(filename):
        if not candidate.is_file():
            continue
        rel = candidate.relative_to(repo_root).as_posix()
        score = suffix_match_score(import_path, rel)
        if score > 0:
            candidates.append((score, len(rel), rel))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    best_score = candidates[0][0]
    best = [item for item in candidates if item[0] == best_score]
    if len(best) == 1:
        return best[0][2]
    return None


def summarize_file(path: Path, repo_root: Path) -> dict:
    text = read_text(path)
    rel = path.relative_to(repo_root).as_posix()
    classes = CLASS_RE.findall(text)
    asset_entries = []
    for import_path in uniq(ASSET_RE.findall(text)):
        asset_entries.append({
            "import_path": import_path,
            "resolved_path": resolve_asset_path(import_path, path, repo_root),
        })
    return {
        "file": rel,
        "assets": asset_entries,
        "testids": uniq(DATA_TESTID_RE.findall(text)),
        "steps": uniq(STEP_RE.findall(text)),
        "texts": uniq(TEXT_RE.findall(text))[:20],
        "style_tokens": uniq(sum((HEX_RE.findall(chunk) for chunk in classes), []))[:20],
    }


def build_prompt(args: argparse.Namespace, summaries: list[dict]) -> str:
    files = "\n".join(f"- {item['file']}" for item in summaries)
    seen_assets: set[tuple[str, str | None]] = set()
    asset_lines: list[str] = []
    for item in summaries:
        for asset in item["assets"]:
            key = (asset["import_path"], asset["resolved_path"])
            if key in seen_assets:
                continue
            seen_assets.add(key)
            if asset["resolved_path"]:
                asset_lines.append(f"- {asset['import_path']} -> {asset['resolved_path']}")
            else:
                asset_lines.append(f"- {asset['import_path']} -> unresolved")
    testids = uniq([tid for item in summaries for tid in item["testids"]])
    steps = uniq([step for item in summaries for step in item["steps"]])
    texts = uniq([txt for item in summaries for txt in item["texts"]])[:16]
    style_tokens = uniq([token for item in summaries for token in item["style_tokens"]])[:16]

    frame_lines = "\n".join(f"- {name}" for name in args.frame) if args.frame else "- create top-level frames based on the code structure"
    ignore_lines = "\n".join(f"- {item}" for item in args.ignore) if args.ignore else "- none"
    third_party_line = args.third_party or "Treat third-party embeds and iframe content as neutral placeholders."

    sections = [
        f"Recreate the `{args.page}` page into a Pencil baseline from code, not from the current runtime screenshot.",
        "",
        "Source files:",
        files,
        "",
        "Output:",
        f"- Target .pen file: {args.pen}",
        "- Top-level frames:",
        frame_lines,
        "",
        "Code-derived assets to respect:",
        *(asset_lines if asset_lines else ["- none found via import scan"]),
        "",
        "Relevant test ids / structure anchors:",
        *([f"- {tid}" for tid in testids] if testids else ["- none found"]),
        "",
        "Relevant state / branch markers:",
        *([f"- {step}" for step in steps] if steps else ["- none found"]),
        "",
        "Relevant texts / placeholders:",
        *([f"- {txt}" for txt in texts] if texts else ["- none found"]),
        "",
        "Relevant style tokens:",
        *([f"- {token}" for token in style_tokens] if style_tokens else ["- none found"]),
        "",
        "Hard rules:",
        "- Prefer code over current runtime screenshot.",
        "- Use actual assets referenced by code when Pencil can render them reliably.",
        f"- {third_party_line}",
        "- Add context/source notes for key frames.",
        "- Make the resulting .pen readable, reviewable, and suitable for further iteration.",
        "",
        "Ignore / exclusions for this phase:",
        ignore_lines,
    ]
    return "\n".join(sections).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a structured prompt for pencil --prompt.")
    parser.add_argument("--page", required=True, help="Logical page name, e.g. login")
    parser.add_argument("--pen", required=True, help="Target .pen file path")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--frame", action="append", default=[], help="Required top-level frame names")
    parser.add_argument("--ignore", action="append", default=[], help="Items intentionally excluded in this phase")
    parser.add_argument("--third-party", default="", help="Rule for third-party embeds / iframes")
    parser.add_argument("--dump-context-json", action="store_true", help="Print the scanned context as JSON instead of the prompt")
    parser.add_argument("--files", nargs="+", required=True, help="Source files to scan")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    files = [Path(f).resolve() for f in args.files]
    summaries = [summarize_file(path, repo_root) for path in files]

    if args.dump_context_json:
        print(json.dumps(summaries, ensure_ascii=False, indent=2))
        return 0

    print(build_prompt(args, summaries), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
