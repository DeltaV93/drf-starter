"""Find every environment variable this project reads.

Used by `apps/core/tests/test_env_documented.py` to keep `.env.example` and
`docs/configuration.md` honest. A configuration reference drifts the moment
someone adds a setting and forgets the docs, and the drift is invisible --
nothing breaks, the variable just quietly has no documented existence.

Parsing rather than grepping, because the reads that get missed are the ones
that wrap:

    UPLOAD_ALLOWED_TYPES = env_list(
        'UPLOAD_ALLOWED_TYPES',
        default=[...],
    )

A line-based search finds the assignment and not the name. `ast` does not
care where the newlines fall.

Run it directly to see what it finds:

    python scripts/env_vars.py
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Where project Python lives. Deliberately not the whole tree: site-packages
# reads hundreds of variables that are nothing to do with this application.
PYTHON_ROOTS = ('apps', 'utils', 'clearpath', 'scripts')
PYTHON_FILES = ('manage.py',)

# Shell and compose files, which read variables Python never sees.
SHELL_FILES = ('entrypoint.sh', 'Dockerfile', 'docker-compose.yml')

# The Vite config reads VITE_ variables as `env.VITE_NAME`, and reads them at
# build time rather than through import.meta.env, so neither the shell pattern
# nor the Python walk sees them.
TS_FILES = ('website/vite.config.ts',)
TS_PATTERN = re.compile(r'\benv\.(VITE_[A-Z0-9_]+)\b')

# The helpers in template/settings/base.py, plus the stdlib calls. Each takes
# the variable name as its first positional argument.
READER_FUNCTIONS = frozenset({'getenv', 'env_bool', 'env_list', 'env_int', 'env_float'})

# `${NAME}` or `$NAME` in a shell file. Three characters minimum and at least
# one underscore-or-digit rules out most of the shell's own single letters.
SHELL_PATTERN = re.compile(r'\$\{?([A-Z][A-Z0-9_]{2,})\b')

# Read by the shell, the platform or a library rather than by this project's
# own code, so they are not settings anyone puts in a .env file.
NOT_SETTINGS = frozenset(
    {
        # Chosen by whatever starts the process, not by a file it reads.
        'DJANGO_SETTINGS_MODULE',
        # Django sets this itself in the autoreloader's child process.
        'RUN_MAIN',
        # Injected by the host. Documented in the deployment guide instead.
        'FLY_APP_NAME',
        'RAILWAY_PUBLIC_DOMAIN',
        'RAILWAY_GIT_COMMIT_SHA',
        'RENDER_EXTERNAL_HOSTNAME',
        'RENDER_GIT_COMMIT',
        # Test-suite plumbing: CI sets it to point the suite at Postgres.
        'DB_ENGINE',
        # Docker build-time only.
        'REQUIREMENTS',
        'PATH',
    }
)


class _EnvVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()

    @staticmethod
    def _literal(node: ast.expr | None) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def visit_Subscript(self, node: ast.Subscript) -> None:
        # os.environ['NAME']
        if (
            isinstance(node.value, ast.Attribute)
            and node.value.attr == 'environ'
            and (name := self._literal(node.slice))
        ):
            self.names.add(name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        # os.environ.get('NAME'), os.getenv('NAME')
        if isinstance(func, ast.Attribute) and func.attr in {'get', *READER_FUNCTIONS}:
            is_environ_get = (
                func.attr == 'get'
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == 'environ'
            )
            if (is_environ_get or func.attr in READER_FUNCTIONS) and node.args:
                if name := self._literal(node.args[0]):
                    self.names.add(name)
        # env_bool('NAME'), env_list('NAME'), ...
        elif isinstance(func, ast.Name) and func.id in READER_FUNCTIONS and node.args:
            if name := self._literal(node.args[0]):
                self.names.add(name)

        self.generic_visit(node)


def _python_files() -> list[Path]:
    files = [BASE_DIR / name for name in PYTHON_FILES]
    for root in PYTHON_ROOTS:
        files.extend(
            path
            for path in (BASE_DIR / root).rglob('*.py')
            # Tests read variables to exercise settings, not to configure them.
            if 'tests' not in path.parts and 'migrations' not in path.parts
        )
    return [path for path in files if path.exists()]


def read_in_python() -> set[str]:
    """Every variable read by this project's own Python."""
    found: set[str] = set()
    for path in _python_files():
        visitor = _EnvVisitor()
        visitor.visit(ast.parse(path.read_text(), filename=str(path)))
        found |= visitor.names
    return found


def read_in_shell() -> set[str]:
    """Every variable referenced by the entrypoint, Dockerfile or compose."""
    found: set[str] = set()
    for name in SHELL_FILES:
        path = BASE_DIR / name
        if path.exists():
            found |= set(SHELL_PATTERN.findall(path.read_text()))
    return found


def read_in_vite_config() -> set[str]:
    """VITE_ variables the Vite config reads directly at build time."""
    found: set[str] = set()
    for name in TS_FILES:
        path = BASE_DIR / name
        if path.exists():
            found |= set(TS_PATTERN.findall(path.read_text()))
    return found


def read_in_spa() -> set[str]:
    """VITE_ variables the SPA reads as `import.meta.env.VITE_NAME`."""
    src = BASE_DIR / 'website' / 'src'
    if not src.exists():
        return set()
    pattern = re.compile(r'import\.meta\.env\.(VITE_[A-Z0-9_]+)')
    found: set[str] = set()
    for path in [*src.rglob('*.ts'), *src.rglob('*.tsx')]:
        if path.name.endswith('.d.ts'):
            continue
        found |= set(pattern.findall(path.read_text()))
    return found


def settings_read() -> set[str]:
    """Everything a person could reasonably put in a .env file."""
    return (
        read_in_python() | read_in_shell() | read_in_vite_config() | read_in_spa()
    ) - NOT_SETTINGS


def backend_settings() -> set[str]:
    """Read by Django, the entrypoint or compose. Belongs in `.env.example`."""
    return {name for name in settings_read() if not name.startswith('VITE_')}


def frontend_settings() -> set[str]:
    """Inlined by Vite at build time. Belongs in `website/.env.example`.

    Separate files because they are consumed at different moments: the
    backend reads its .env when the process starts, and can be changed by
    restarting it. A VITE_ variable is baked into the bundle, so changing one
    means rebuilding the image.
    """
    return {name for name in settings_read() if name.startswith('VITE_')}


def _names_in_env_file(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(re.findall(r'^#?\s*([A-Z][A-Z0-9_]*)=', path.read_text(), flags=re.MULTILINE))


def documented_in_env_example() -> set[str]:
    """Names either .env.example mentions, commented out or not."""
    return _names_in_env_file(BASE_DIR / '.env.example') | _names_in_env_file(
        BASE_DIR / 'website' / '.env.example'
    )


def documentable() -> set[str]:
    """Everything the reference may list.

    Wider than `settings_read()`: the reference also has a section for the
    variables a platform injects, which are read but are not yours to set.
    """
    return settings_read() | NOT_SETTINGS


def documented_in_reference() -> set[str]:
    """Names `docs/configuration.md` lists, as `| \\`NAME\\` |` table rows."""
    path = BASE_DIR / 'docs' / 'configuration.md'
    if not path.exists():
        return set()
    return set(re.findall(r'^\|\s*`([A-Z][A-Z0-9_]*)`', path.read_text(), flags=re.MULTILINE))


if __name__ == '__main__':
    read = settings_read()
    env_example = documented_in_env_example()
    reference = documented_in_reference()

    print(
        f'{len(read)} settings read: {len(backend_settings())} backend, '
        f'{len(frontend_settings())} frontend\n'
    )
    for group, missing in (
        ('the .env.example files', read - env_example),
        ('docs/configuration.md', read - reference),
    ):
        print(f'Read but absent from {group}: {sorted(missing) or "none"}')
    for group, extra in (
        ('the .env.example files', env_example - read),
        ('docs/configuration.md', reference - documentable()),
    ):
        print(f'Listed in {group} but never read: {sorted(extra) or "none"}')
