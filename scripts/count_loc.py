#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "storage",
    ".git-rewrite",
}


def count_file(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="ignore").splitlines())


def iter_files(base: Path, suffix: str) -> list[Path]:
    files: list[Path] = []
    for path in base.rglob(f"*{suffix}"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def section(label: str, files: list[Path]) -> tuple[str, int, int]:
    lines = sum(count_file(path) for path in files)
    return label, len(files), lines


groups = [
    section("Python (app/)", iter_files(ROOT / "app", ".py")),
    section("Python (tests/)", iter_files(ROOT / "tests", ".py")),
    section("Python (scripts/)", iter_files(ROOT / "scripts", ".py")),
    section("Alembic migrations", iter_files(ROOT / "alembic", ".py")),
]

config_files = [
    ROOT / "README.md",
    ROOT / "Dockerfile",
    ROOT / "docker-compose.yml",
    ROOT / "requirements.txt",
    ROOT / "requirements-dev.txt",
    ROOT / "pytest.ini",
    ROOT / "alembic.ini",
    ROOT / ".env.example",
    ROOT / ".github/workflows/ci.yml",
]
config_files = [path for path in config_files if path.exists()]
groups.append(section("Config & docs", config_files))

total_files = 0
total_lines = 0
print("Lines of code breakdown:\n")
for label, files, lines in groups:
    print(f"  {label:22} {files:4} files  {lines:6,} lines")
    total_files += files
    total_lines += lines

print(f"\n  {'TOTAL':22} {total_files:4} files  {total_lines:6,} lines")
