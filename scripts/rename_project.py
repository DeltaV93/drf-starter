#!/usr/bin/env python
"""Rename this template to your own project.

The Django project package ships as `template`, which is fine for a starter
and wrong for a real project. This renames the package directory, rewrites
every reference to it, and substitutes the display name that appears in the
API docs, the browser tab and the UI.

    python scripts/rename_project.py myapp
    python scripts/rename_project.py myapp --display-name "My App"
    python scripts/rename_project.py myapp --dry-run

Run it from the repository root, on a clean working tree, before you start
building. It touches tracked source files only -- not .git, .venv, or
node_modules.
"""

from __future__ import annotations

import argparse
import keyword
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

OLD_PACKAGE = 'template'
OLD_DISPLAY_NAME = 'DRF Starter'

# Directories never descended into.
SKIP_DIRS = {
    '.git',
    '.venv',
    'venv',
    'env',
    '__pycache__',
    'node_modules',
    'dist',
    'staticfiles',
    'media',
    '.pytest_cache',
    '.ruff_cache',
    'htmlcov',
    'coverage',
    '.mypy_cache',
}

# Only these extensions are rewritten; everything else is left byte-identical.
TEXT_SUFFIXES = {
    '.py',
    '.ts',
    '.tsx',
    '.js',
    '.jsx',
    '.json',
    '.yml',
    '.yaml',
    '.toml',
    '.cfg',
    '.ini',
    '.md',
    '.html',
    '.txt',
    '.sh',
    '.env',
    '.example',
}

EXTRA_FILES = {'Dockerfile', 'Makefile', '.env.example', '.dockerignore', '.gitignore'}

# Substrings that identify the project package, longest first so that e.g.
# 'template.settings' is rewritten before a bare 'template'.
PACKAGE_PATTERNS = [
    r'\btemplate\.settings\b',
    r'\btemplate\.wsgi\b',
    r'\btemplate\.asgi\b',
    r'\btemplate\.urls\b',
    r'\btemplate\.celery\b',
    r"(?<=-A )template\b",
    r"(?<=Celery\(')template(?=')",
    r"(?<=')template(?=/)",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('name', help='New Python package name, e.g. myapp (lowercase, no spaces)')
    parser.add_argument(
        '--display-name',
        help='Human-readable name for the UI and API docs. Defaults to a title-cased `name`.',
    )
    parser.add_argument('--dry-run', action='store_true', help='Report what would change and stop')
    parser.add_argument('--force', action='store_true', help='Proceed even with a dirty working tree')
    return parser.parse_args(argv)


def validate_name(name: str) -> str:
    if not re.fullmatch(r'[a-z][a-z0-9_]*', name):
        sys.exit(
            f'Invalid package name {name!r}: use lowercase letters, digits and '
            'underscores, starting with a letter.'
        )
    if keyword.iskeyword(name):
        sys.exit(f'{name!r} is a Python keyword.')
    if name == OLD_PACKAGE:
        sys.exit('That is already the package name; nothing to do.')
    if (REPO_ROOT / name).exists():
        sys.exit(f'{name}/ already exists in the repository root.')
    return name


def working_tree_is_clean() -> bool:
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        # Not a git repo, or git is unavailable: nothing to check against.
        return True
    return not result.stdout.strip()


def iter_text_files():
    this_file = Path(__file__).resolve()
    for path in REPO_ROOT.rglob('*'):
        if not path.is_file():
            continue
        # Never rewrite this script: it holds the OLD_PACKAGE constants the
        # rewrite depends on, and it is running.
        if path.resolve() == this_file:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(REPO_ROOT).parts):
            continue
        if path.suffix in TEXT_SUFFIXES or path.name in EXTRA_FILES:
            yield path


def rewrite(content: str, new_package: str, new_display_name: str) -> str:
    for pattern in PACKAGE_PATTERNS:
        content = re.sub(pattern, lambda m: m.group(0).replace(OLD_PACKAGE, new_package), content)

    # Bare references in settings paths and Docker/Make commands.
    content = re.sub(rf"\b{OLD_PACKAGE}(?=\.(settings|wsgi|asgi|urls|celery))", new_package, content)
    content = content.replace(f"'{OLD_PACKAGE}'", f"'{new_package}'")
    content = content.replace(f'"{OLD_PACKAGE}"', f'"{new_package}"')
    content = content.replace(f'{OLD_PACKAGE}.wsgi', f'{new_package}.wsgi')
    content = content.replace(f'{OLD_PACKAGE}.asgi', f'{new_package}.asgi')
    content = content.replace(f'-A {OLD_PACKAGE}', f'-A {new_package}')

    content = content.replace(OLD_DISPLAY_NAME, new_display_name)
    return content


def main(argv=None):
    args = parse_args(argv)
    new_package = validate_name(args.name)
    new_display_name = args.display_name or args.name.replace('_', ' ').title()

    if not args.dry_run and not args.force and not working_tree_is_clean():
        sys.exit(
            'Working tree is not clean. Commit or stash first so the rename is '
            'easy to review and undo, or pass --force.'
        )

    changed = []
    for path in iter_text_files():
        try:
            original = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue

        updated = rewrite(original, new_package, new_display_name)
        if updated == original:
            continue

        changed.append(path.relative_to(REPO_ROOT))
        if not args.dry_run:
            path.write_text(updated, encoding='utf-8')

    package_dir = REPO_ROOT / OLD_PACKAGE
    will_move = package_dir.is_dir()

    if args.dry_run:
        print(f'Would rename package: {OLD_PACKAGE}/ -> {new_package}/' if will_move else 'Package directory not found.')
        print(f'Would set display name: {OLD_DISPLAY_NAME!r} -> {new_display_name!r}')
        print(f'Would rewrite {len(changed)} file(s):')
        for path in sorted(changed):
            print(f'  {path}')
        return 0

    if will_move:
        moved = False
        try:
            subprocess.run(
                ['git', 'mv', OLD_PACKAGE, new_package], cwd=REPO_ROOT, check=True, capture_output=True
            )
            moved = True
        except (OSError, subprocess.CalledProcessError):
            pass
        if not moved:
            package_dir.rename(REPO_ROOT / new_package)

    print(f'Renamed package {OLD_PACKAGE}/ -> {new_package}/')
    print(f'Display name is now {new_display_name!r}')
    print(f'Rewrote {len(changed)} file(s).')
    print()
    print('Next:')
    print('  1. Review the diff:  git diff')
    print('  2. Re-run the suite: make test')
    print('  3. Delete this script -- a project only gets renamed once:')
    print('       git rm scripts/rename_project.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
