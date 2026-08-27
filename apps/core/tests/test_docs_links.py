"""Internal documentation links resolve.

A link to a renamed file is invisible: the docs still build, the page still
reads correctly, and the reader only finds out when they click. Cross-document
links are the first thing to break when a file moves, and the last thing anyone
checks.

Only internal targets. External URLs are not fetched -- a test suite that
depends on the network is a test suite that fails on a train.
"""

import re
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[3]

MARKDOWN_FILES = [
    BASE_DIR / 'README.md',
    BASE_DIR / 'CLAUDE.md',
    BASE_DIR / 'CONTRIBUTING.md',
    *sorted((BASE_DIR / 'docs').glob('*.md')),
]

LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
HEADING = re.compile(r'^#+\s+(.+?)\s*$', re.MULTILINE)


def _anchors(text):
    """GitHub's slugs: lowercase, punctuation dropped, spaces to hyphens.

    Underscores survive, which is easy to get wrong and matters here: the
    documentation is full of headings named after SNAKE_CASE settings, and
    `### FRONTEND_URL in detail` anchors as `#frontend_url-in-detail`. Dropping
    the underscore made this test reject a link that works and accept one that
    does not -- in the same direction, so nothing looked broken until the first
    such heading was written.
    """
    slugs = set()
    for heading in HEADING.findall(text):
        # Inline code and links appear in headings; their markup is not slugged.
        plain = re.sub(r'`([^`]*)`', r'\1', heading)
        plain = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', plain)
        slugs.add(re.sub(r'[^a-z0-9 _-]', '', plain.lower()).replace(' ', '-'))
    return slugs


@pytest.mark.parametrize(
    'markdown', [path for path in MARKDOWN_FILES if path.exists()], ids=lambda p: p.name
)
def test_internal_links_resolve(markdown):
    text = markdown.read_text()
    own_anchors = _anchors(text)
    broken = []

    for label, target in LINK.findall(text):
        if target.startswith(('http://', 'https://', 'mailto:', '#!')):
            continue

        path_part, _, anchor = target.partition('#')

        if not path_part:
            if anchor and anchor not in own_anchors:
                broken.append(f'[{label}](#{anchor}) -- no such heading in this file')
            continue

        resolved = (markdown.parent / path_part).resolve()
        if not resolved.exists():
            broken.append(f'[{label}]({target}) -- {path_part} does not exist')
        elif anchor and resolved.suffix == '.md':
            if anchor not in _anchors(resolved.read_text()):
                broken.append(f'[{label}]({target}) -- {path_part} has no such heading')

    assert not broken, f'Broken links in {markdown.name}:\n  ' + '\n  '.join(broken)
