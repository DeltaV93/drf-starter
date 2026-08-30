"""Renaming the template actually renames everything a user sees.

`scripts/rename_project.py` is run exactly once per project, by someone who
has just cloned and has no idea what the repository normally looks like. If it
misses a file, the symptom is the template's own name sitting in their nav bar
with nothing in the diff to explain it -- and by then the script has usually
been deleted, as its own closing message advises.

It had no tests. That is the gap worth closing rather than any single bug: the
display name lives in `packages/shared/src/brand.ts` only because the theming
work put it there, and nothing would have failed if that file had been outside
the script's reach. It has since moved once already -- out of `website/src/`
and into the package the mobile app shares -- which is the second argument for
pinning it here rather than trusting the script's reach.

Everything below runs against a throwaway copy of the repository, renamed
once for the whole module. Nothing touches the working tree.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

NEW_PACKAGE = 'acme'
NEW_DISPLAY_NAME = 'Acme Cloud'
OLD_DISPLAY_NAME = 'DRF Starter'

# Copying the whole repository would mean the virtualenv and node_modules.
IGNORED = shutil.ignore_patterns(
    '.git',
    '.venv',
    'venv',
    'node_modules',
    'dist',
    '__pycache__',
    '.pytest_cache',
    '.ruff_cache',
    'htmlcov',
    'staticfiles',
    '*.sqlite3',
)


def _copy_repo(destination):
    shutil.copytree(REPO_ROOT, destination, ignore=IGNORED, dirs_exist_ok=True)
    return destination


def _rename(root, *extra):
    """Run the real script against a copy, and return its output.

    `--force` skips the clean-working-tree check, which has nothing to say
    about a directory that is not a git repository.
    """
    result = subprocess.run(
        [
            sys.executable,
            'scripts/rename_project.py',
            NEW_PACKAGE,
            '--display-name',
            NEW_DISPLAY_NAME,
            '--force',
            *extra,
        ],
        capture_output=True,
        text=True,
        cwd=root,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


@pytest.fixture(scope='module')
def renamed(tmp_path_factory):
    """A copy of the repository, renamed once."""
    root = _copy_repo(tmp_path_factory.mktemp('renamed') / 'repo')
    _rename(root)
    return root


# ---------------------------------------------------------------------------
# What the user sees.
# ---------------------------------------------------------------------------


def test_the_product_name_is_renamed_at_its_single_source(renamed):
    """The one that prompted these tests.

    `identity.name` is what every chrome component renders. It arrived with
    the theming work, long after this script was written, and nothing checked
    that the script could still reach it.
    """
    brand = (renamed / 'packages' / 'shared' / 'src' / 'brand.ts').read_text()

    assert f"name: '{NEW_DISPLAY_NAME}'" in brand
    assert OLD_DISPLAY_NAME not in brand


# Everywhere the product name is shown as page chrome. Both were reported
# separately -- the nav bar first, the footer second -- which is the argument
# for listing them rather than testing whichever one someone happened to
# notice.
NAME_IS_DISPLAYED_IN = ['Header.tsx', 'Footer.tsx']


@pytest.mark.parametrize('component', NAME_IS_DISPLAYED_IN)
def test_each_place_the_name_appears_reads_it_from_the_brand_file(renamed, component):
    """Guards the test above, once per surface.

    Renaming `brand.ts` proves nothing about a component that has since
    hardcoded the name instead: the rename would pass, the tests would be
    green, and that one corner of the UI would keep the template's name. Which
    is exactly what a reader of this suite would assume could not happen.
    """
    source = (renamed / 'website' / 'src' / 'components' / 'layout' / component).read_text()

    assert 'identity.name' in source, f'{component} no longer reads the shared name'
    assert OLD_DISPLAY_NAME not in source


def test_no_other_component_displays_a_product_name_of_its_own(renamed):
    """Catches a third surface being added without a third test.

    The list above has to be maintained by hand; this does not. Anything under
    `components/` mentioning the template's name is either a hardcoded string
    the rename cannot reach, or a stale comment.
    """
    components = renamed / 'website' / 'src' / 'components'

    offenders = [
        path.relative_to(renamed)
        for path in components.rglob('*.tsx')
        if OLD_DISPLAY_NAME in path.read_text(encoding='utf-8', errors='ignore')
    ]

    assert not offenders, 'hardcoded product name in:\n  ' + '\n  '.join(
        str(p) for p in sorted(offenders)
    )


def test_the_api_title_is_renamed(renamed):
    """What a reader of /api/docs/ sees."""
    assert f'API_TITLE={NEW_DISPLAY_NAME} API' in (renamed / '.env.example').read_text()


def test_no_source_file_still_carries_the_old_display_name(renamed):
    """The catch-all, so a new file is covered without a new test.

    The script itself is exempt: it has to keep knowing what it is replacing.
    """
    script = renamed / 'scripts' / 'rename_project.py'
    suffixes = {'.py', '.ts', '.tsx', '.html', '.json', '.md', '.yml', '.example'}

    offenders = []
    for path in renamed.rglob('*'):
        if not path.is_file() or path.suffix not in suffixes or path == script:
            continue
        if any(part in {'node_modules', 'dist', '__pycache__'} for part in path.parts):
            continue
        if OLD_DISPLAY_NAME in path.read_text(encoding='utf-8', errors='ignore'):
            offenders.append(path.relative_to(renamed))

    assert not offenders, 'still carrying the template name:\n  ' + '\n  '.join(
        str(p) for p in sorted(offenders)
    )


# ---------------------------------------------------------------------------
# The package itself.
# ---------------------------------------------------------------------------


def test_the_package_directory_is_moved(renamed):
    assert (renamed / NEW_PACKAGE / 'settings').is_dir()
    assert not (renamed / 'template').exists()


def test_the_dotted_references_follow_the_package(renamed):
    """`template.settings` in manage.py or the Dockerfile would leave a
    project that renames cleanly and then cannot start."""
    manage = (renamed / 'manage.py').read_text()

    assert f'{NEW_PACKAGE}.settings' in manage
    assert 'template.settings' not in manage


def test_the_asgi_entry_point_the_container_names_is_renamed(renamed):
    """The Dockerfile's CMD names the module. Miss it and the image builds,
    deploys, and fails to start."""
    dockerfile = (renamed / 'Dockerfile').read_text()

    assert f'{NEW_PACKAGE}.asgi:application' in dockerfile
    assert 'template.asgi' not in dockerfile


# ---------------------------------------------------------------------------
# The stale build, which is what actually leaves the old name on screen.
# ---------------------------------------------------------------------------


def test_a_stale_frontend_build_is_reported(tmp_path):
    """The rename rewrites source; `website/dist` is generated and skipped.

    Django serves that directory whenever it exists, and the display name is
    compiled into the bundle -- so renaming with a build lying around leaves
    the old name in the nav bar, with nothing in the diff to explain it. The
    script cannot fix that without rewriting minified output, so it has to say
    so instead.
    """
    root = _copy_repo(tmp_path / 'repo')
    dist = root / 'website' / 'dist'
    dist.mkdir(parents=True, exist_ok=True)
    (dist / 'index.html').write_text(f'<title>{OLD_DISPLAY_NAME}</title>')

    output = _rename(root)

    assert 'website/dist' in output
    assert 'make fe-build' in output


def test_nothing_is_said_when_there_is_no_build(tmp_path):
    """Guards the test above. A fresh clone has no `dist`, and a warning about
    rebuilding something that was never built is noise on the one run that
    matters most."""
    root = _copy_repo(tmp_path / 'repo')
    shutil.rmtree(root / 'website' / 'dist', ignore_errors=True)

    output = _rename(root)

    assert 'make fe-build' not in output
