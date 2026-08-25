"""Where the metadata document is reachable.

Mounted at the project root, not under `/api/v1/`: a well-known URI is fixed
by the RFC and cannot carry a version prefix.

Two patterns for one document. `metadata.py` explains the derivation -- the
well-known segment is inserted between the origin and the resource's path, so
a resource at `/mcp` publishes at `/.well-known/oauth-protected-resource/mcp`.
The bare form is served too because a resource identifier with no path
produces exactly that.
"""

from django.urls import path, re_path

from .metadata import WELL_KNOWN
from .views import ProtectedResourceMetadataView

# Django patterns are written without the leading slash.
_well_known = WELL_KNOWN.lstrip('/')

urlpatterns = [
    path(
        _well_known,
        ProtectedResourceMetadataView.as_view(),
        name='oauth-protected-resource',
    ),
    # Any resource path beneath it. There is one resource, so the suffix is
    # accepted rather than matched -- a second one would need a lookup here.
    re_path(
        rf'^{_well_known}/.*$',
        ProtectedResourceMetadataView.as_view(),
        name='oauth-protected-resource-path',
    ),
]
