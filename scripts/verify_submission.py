#!/usr/bin/env python3
"""Pre-upload checks for Silver / AfterQuery repo submission."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = (
    "Dockerfile",
    "docker-compose.yml",
    "requirements.txt",
    "requirements-dev.txt",
    "pytest.ini",
    ".env.example",
    ".gitignore",
    "alembic.ini",
    "app/main.py",
    "tests/conftest.py",
)

FORBIDDEN_TRACKED = (
    ".env",
)


def check_paths() -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_PATHS:
        if not (ROOT / relative).exists():
            errors.append(f"Missing required file: {relative}")
    return errors


def check_git_present() -> list[str]:
    if not (ROOT / ".git").exists():
        return ["Missing .git directory (Silver expects full git history in zip)"]
    return []


def check_forbidden_tracked() -> list[str]:
    errors: list[str] = []
    for relative in FORBIDDEN_TRACKED:
        path = ROOT / relative
        if not path.exists():
            continue
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", relative],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            errors.append(f"Tracked secret-like file must not be in git: {relative}")
    return errors


def run_tests() -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output.strip()


def main() -> int:
    errors = [
        *check_paths(),
        *check_git_present(),
        *check_forbidden_tracked(),
    ]

    if errors:
        print("Submission checks failed:\n")
        for error in errors:
            print(f"  - {error}")
        return 1

    passed, output = run_tests()
    if not passed:
        print("Pytest failed:\n")
        print(output)
        return 1

    print("Submission checks passed.")
    print(output.splitlines()[-1] if output else "pytest completed")
    print("\nUpload checklist:")
    print("  - Zip the repo root including .git/")
    print("  - Do not include .env or storage/resumes/")
    print("  - Upload language: Python")
    print("  - Upload Dockerfile separately if the form requires it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
