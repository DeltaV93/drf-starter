"""A log that can be rewritten answers no question it was kept for."""

import pytest
from django.utils import timezone

from apps.audit.models import Action, AuditEvent
from apps.core.audit import AuditAction, audit
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_an_existing_event_cannot_be_saved_again():
    event = audit(AuditAction.LOGIN_SUCCEEDED, actor=UserFactory())

    event.action = Action.LOGOUT
    with pytest.raises(ValueError, match='append-only'):
        event.save()

    event.refresh_from_db()
    assert event.action == Action.LOGIN_SUCCEEDED


def test_an_event_cannot_be_deleted():
    event = audit(AuditAction.LOGIN_SUCCEEDED, actor=UserFactory())

    with pytest.raises(ValueError, match='append-only'):
        event.delete()

    assert AuditEvent.objects.filter(pk=event.pk).exists()


def test_the_admin_allows_neither_adding_editing_nor_deleting():
    from django.contrib.admin.sites import AdminSite

    from apps.audit.admin import AuditEventAdmin

    admin = AuditEventAdmin(AuditEvent, AdminSite())

    assert admin.has_add_permission(None) is False
    assert admin.has_change_permission(None) is False
    assert admin.has_delete_permission(None) is False


def test_deleting_the_actor_keeps_the_record():
    """The entry saying an account was deleted is often the one that matters."""
    user = UserFactory(email='gone@example.com')
    event = audit(AuditAction.ACCOUNT_DELETED, actor=user)

    user.delete()

    event.refresh_from_db()
    assert event.actor is None
    # The label is a copy, so the record still says who.
    assert event.actor_label == 'gone@example.com'


# --------------------------------------------------------------------------
# Retention
# --------------------------------------------------------------------------


def test_pruning_drops_only_entries_past_the_window():
    from datetime import timedelta

    from django.core.management import call_command

    old = audit(AuditAction.LOGIN_SUCCEEDED, actor=UserFactory())
    recent = audit(AuditAction.LOGIN_SUCCEEDED, actor=UserFactory())

    AuditEvent.objects.filter(pk=old.pk).update(
        created_at=timezone.now() - timedelta(days=400)
    )

    call_command('prune_audit_log', days=365)

    assert not AuditEvent.objects.filter(pk=old.pk).exists()
    assert AuditEvent.objects.filter(pk=recent.pk).exists()


def test_a_dry_run_deletes_nothing():
    from datetime import timedelta

    from django.core.management import call_command

    old = audit(AuditAction.LOGIN_SUCCEEDED, actor=UserFactory())
    AuditEvent.objects.filter(pk=old.pk).update(
        created_at=timezone.now() - timedelta(days=400)
    )

    call_command('prune_audit_log', days=365, dry_run=True)

    assert AuditEvent.objects.filter(pk=old.pk).exists()


def test_a_zero_retention_window_deletes_nothing():
    """Guards against a misconfiguration wiping the table."""
    from django.core.management import call_command

    event = audit(AuditAction.LOGIN_SUCCEEDED, actor=UserFactory())

    call_command('prune_audit_log', days=0)

    assert AuditEvent.objects.filter(pk=event.pk).exists()
