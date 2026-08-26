"""A user's authorisation for one outbound MCP server.

Scoped to `AUTH_USER_MODEL` and nothing else. No foreign key into any other
optional app, which is what lets this one be removed on its own -- the same
rule every optional feature here follows.

**The row holds a credential, not a connection.** Which servers exist, where
they live and which tools they expose all come from `servers/`, in the
repository, reviewable in a diff. A row can only say "this user authorised
that server" and carry the token. A stolen database therefore cannot point the
application at a server nobody approved.
"""

from django.conf import settings
from django.db import models

from utils.crypto import decrypt, encrypt


def _key_material():
    """The material a stored credential is encrypted with.

    ENCRYPTION NOTE: MCP_CLIENT_SECRET_KEY falls back to SECRET_KEY, so
    rotating SECRET_KEY makes every stored credential undecryptable and every
    connection has to be re-authorised. That is recoverable -- unlike the
    two-factor case, where the same fallback locks users out -- but it is
    still a surprise. Set MCP_CLIENT_SECRET_KEY explicitly if you will ever
    rotate.
    """
    return getattr(settings, 'MCP_CLIENT_SECRET_KEY', '') or settings.SECRET_KEY


class ConnectedServer(models.Model):
    """One user's authorisation for one server slug."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='connected_mcp_servers',
    )
    # The slug from a module under servers/. Deliberately a plain CharField
    # with no database-level constraint tying it to the registry: a definition
    # can be removed from the code while rows still reference it, and a
    # dangling row must not break the migration that removes it. The registry
    # is the authority; a row for an unknown slug is simply ignored.
    slug = models.CharField(max_length=64)
    # Off is not the same as absent: disconnecting keeps the token so
    # reconnecting does not mean re-authorising, while `enabled` decides
    # whether the client will use it.
    enabled = models.BooleanField(default=True)
    # Encrypted at rest. It is a bearer credential for a third-party service:
    # a database dump alone should not be enough to act as this user there.
    encrypted_credential = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'slug'], name='unique_mcp_connection_per_user'
            )
        ]
        ordering = ['slug']

    def __str__(self):
        return f'{self.user} -> {self.slug}'

    def set_credential(self, raw: str) -> None:
        self.encrypted_credential = encrypt(raw, _key_material()) if raw else ''

    @property
    def credential(self) -> str | None:
        """The token, or None if there is none or it will not decrypt.

        None on a decryption failure rather than an exception: every caller
        has to fail closed, and a credential that cannot be read is the same
        as not having one.
        """
        if not self.encrypted_credential:
            return None
        return decrypt(self.encrypted_credential, _key_material())
