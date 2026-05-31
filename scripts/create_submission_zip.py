#!/usr/bin/env python3
"""Create a Silver-ready zip of the repository."""

from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from datetime import datetime
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


def create_zip(output_path: Path) -> int:
    if not (ROOT / ".git").exists():
        print("Error: .git/ is missing. Silver requires full git history in the zip.")
        return 1

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_dir():
                continue
            if should_skip(path):
                continue
            archive.write(path, path.relative_to(ROOT).as_posix())

    print(f"Created {output_path}")
    print(f"Size: {output_path.stat().st_size / (1024 * 1024):.2f} MB")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Silver submission zip")
    default_name = f"AI-Powered-Hiring-Intelligence-Systems-{datetime.now():%Y%m%d}.zip"
    parser.add_argument(
        "-o",
        "--output",
        default=str(ROOT.parent / default_name),
        help="Output zip path",
    )
    args = parser.parse_args()

    verify = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_submission.py")],
        cwd=ROOT,
    )
    if verify.returncode != 0:
        print("Fix verification errors before creating the zip.")
        return verify.returncode

    return create_zip(Path(args.output))


if __name__ == "__main__":
    raise SystemExit(main())
