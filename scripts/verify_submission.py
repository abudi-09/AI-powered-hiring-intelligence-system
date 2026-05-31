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
    ".github/workflows/ci.yml",
    "scripts/create_admin.py",
    "scripts/docker-entrypoint.sh",
    "scripts/wait_for_db.py",
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


def check_dockerignore_allows_git() -> list[str]:
    path = ROOT / ".dockerignore"
    if not path.exists():
        return []
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    blocked = {".git", ".git/", ".git/**"}
    if any(line in blocked or line.rstrip("/") == ".git" for line in lines):
        return [".dockerignore must not exclude .git/ (Silver task runs need git history)"]
    return []


def check_dockerfile_basics() -> list[str]:
    path = ROOT / "Dockerfile"
    if not path.exists():
        return []
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    if len(text.encode("utf-8")) > 20 * 1024:
        errors.append("Dockerfile exceeds Silver 20 KB size limit")
    if text.count("\n") + 1 > 200:
        errors.append("Dockerfile exceeds Silver 200 line limit")
    if "COPY . ." not in text:
        errors.append("Dockerfile should use COPY . . at repo root")
    if "--no-install-recommends" not in text:
        errors.append("Dockerfile apt-get lines must use --no-install-recommends")
    first_from = next((line for line in text.splitlines() if line.strip().startswith("FROM")), "")
    if first_from and (first_from.endswith(":latest") or first_from.strip() == "FROM python"):
        errors.append("Dockerfile base image must be pinned (no :latest or bare tag)")
    return errors


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
        *check_dockerignore_allows_git(),
        *check_dockerfile_basics(),
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
    print("  - Run: python scripts/create_submission_zip.py")
    print("  - Or zip the repo root including .git/")
    print("  - Do not include .env, .venv/, storage/, or __pycache__/")
    print("  - Upload language: Python")
    print("  - Upload Dockerfile separately if the form requires it")
    print("  - Keep the GitHub repo private")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
