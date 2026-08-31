"""Comparing the dotted version strings app stores use.

Not `packaging.version`: that implements PEP 440, where `1.0.0-beta` sorts
*before* `1.0.0` and `1.0.0.post1` after it. App versions are not Python
versions. Apple wants CFBundleShortVersionString as one to three integers, and
Play's versionName is free-form but conventionally the same. Comparing them as
a tuple of integers is the whole rule.
"""

from __future__ import annotations

import re

_LEADING_INTEGERS = re.compile(r'^\d+(?:\.\d+)*')


def parse(version: str) -> tuple[int, ...] | None:
    """Return the numeric components, or None if there are none to read.

    Anything after the numbers is ignored -- `1.2.3-hotfix` compares as
    (1, 2, 3). Ignoring a suffix is the safe direction: the alternative is
    refusing to compare, and a version this cannot read must never be treated
    as below the minimum, because that would lock a user out of an app that is
    probably newer than the gate rather than older.
    """
    match = _LEADING_INTEGERS.match(version.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.group().split('.'))


def is_at_least(version: str, minimum: str) -> bool:
    """Is `version` the same as or newer than `minimum`?

    Missing components count as zero, so `1.2` is `1.2.0` and satisfies a
    minimum of `1.2`. Unreadable input answers True -- see `parse`.
    """
    left, right = parse(version), parse(minimum)
    if left is None or right is None:
        return True
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)) >= right + (0,) * (width - len(right))


class Requirement:
    """The three answers the gate can give.

    Not a model field: it is computed per request from the caller's own
    version and never stored.
    """

    NONE = 'none'
    RECOMMENDED = 'recommended'
    REQUIRED = 'required'

    CHOICES = [NONE, RECOMMENDED, REQUIRED]


def requirement_for(version: str, minimum: str, recommended: str) -> str:
    """What a client running `version` should do about these two floors.

    A plain function rather than a model method because the view answers from
    a cache of the row's fields rather than the row -- and two copies of this
    comparison, one per caller, is exactly the drift that ends with the block
    firing in one place and not the other.
    """
    if minimum and not is_at_least(version, minimum):
        return Requirement.REQUIRED
    if recommended and not is_at_least(version, recommended):
        return Requirement.RECOMMENDED
    return Requirement.NONE
