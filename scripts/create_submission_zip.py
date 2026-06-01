#!/usr/bin/env python3
"""Create a Silver-ready zip of the repository."""

from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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
    """Derive inner folder from zip name, e.g. talentforge-submit.zip -> talentforge."""
    stem = output_path.stem
    if stem.endswith("-submit"):
        return stem[: -len("-submit")]
    return stem


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
            archive.write(path, f"{inner}/{relative}")

    print(f"Created {output_path}")
    print(f"Inner folder: {inner}/")
    print(f"Size: {output_path.stat().st_size / (1024 * 1024):.2f} MB")
    return 0


def default_output_name() -> str:
    return "talentforge-submit.zip"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Silver submission zip")
    parser.add_argument(
        "-o",
        "--output",
        default=str(ROOT.parent / default_output_name()),
        help="Output zip path (default: talentforge-submit.zip)",
    )
    parser.add_argument(
        "--folder",
        default=None,
        help="Root folder inside the zip (default: derived from zip name, e.g. talentforge)",
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
