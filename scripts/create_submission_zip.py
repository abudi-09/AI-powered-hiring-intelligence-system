#!/usr/bin/env python3
"""Create a Silver-ready zip of the repository."""

from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Rewrite git metadata in the zip so remote URL matches the branded repo name.
GIT_REPO_NAME_FROM = "AI-Powered-Hiring-Intelligence-Systems"
GIT_REPO_NAME_TO = "meridian-platform"
GITHUB_OWNER = "abudi-09"

EXCLUDE_DIR_NAMES = {
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    ".git-rewrite",
    "storage",
}

EXCLUDE_FILE_NAMES = {
    ".env",
    ".coverage",
}

EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".log", ".swp", ".bak")


def should_skip(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    parts = relative.parts
    if any(part in EXCLUDE_DIR_NAMES for part in parts):
        return True
    if path.name in EXCLUDE_FILE_NAMES:
        return True
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    return False


def folder_name_from_zip(output_path: Path) -> str:
    """Derive inner folder from zip name, e.g. meridian-platform-submit.zip -> meridian-platform."""
    stem = output_path.stem
    if stem.endswith("-submit"):
        return stem[: -len("-submit")]
    return stem


def rewrite_git_text(content: str) -> str:
    updated = content.replace(GIT_REPO_NAME_FROM, GIT_REPO_NAME_TO)
    updated = updated.replace(
        GIT_REPO_NAME_FROM.lower(),
        GIT_REPO_NAME_TO,
    )
    return updated


def read_archive_bytes(path: Path) -> bytes:
    if ".git" not in path.parts:
        return path.read_bytes()
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return path.read_bytes()
    if GIT_REPO_NAME_FROM not in text and GIT_REPO_NAME_FROM.lower() not in text:
        return path.read_bytes()
    return rewrite_git_text(text).encode("utf-8")


def create_zip(output_path: Path, *, root_folder: str | None = None) -> int:
    if not (ROOT / ".git").exists():
        print("Error: .git/ is missing. Silver requires full git history in the zip.")
        return 1

    inner = (root_folder or folder_name_from_zip(output_path)).strip("/\\")
    if not inner:
        print("Error: inner folder name cannot be empty.")
        return 1

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_dir():
                continue
            if should_skip(path):
                continue
            relative = path.relative_to(ROOT).as_posix()
            archive.writestr(f"{inner}/{relative}", read_archive_bytes(path))

    print(f"Created {output_path}")
    print(f"Inner folder: {inner}/")
    print(f"Git remote in zip: https://github.com/{GITHUB_OWNER}/{GIT_REPO_NAME_TO}.git")
    print(f"Size: {output_path.stat().st_size / (1024 * 1024):.2f} MB")
    return 0


def default_output_name() -> str:
    return "meridian-platform-submit.zip"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Silver submission zip")
    parser.add_argument(
        "-o",
        "--output",
        default=str(ROOT.parent / default_output_name()),
        help="Output zip path (default: meridian-platform-submit.zip)",
    )
    parser.add_argument(
        "--folder",
        default=None,
        help="Root folder inside the zip (default: derived from zip name, e.g. meridian-platform)",
    )
    args = parser.parse_args()

    verify = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_submission.py")],
        cwd=ROOT,
    )
    if verify.returncode != 0:
        print("Fix verification errors before creating the zip.")
        return verify.returncode

    return create_zip(Path(args.output), root_folder=args.folder)


if __name__ == "__main__":
    raise SystemExit(main())
