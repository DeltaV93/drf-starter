from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

pytestmark = pytest.mark.django_db


def _report():
    out = StringIO()
    call_command('generate_monthly_report', stdout=out)
    return out.getvalue()


def test_report_runs_with_no_data():
    output = _report()

    assert 'Active subscriptions: 0' in output
    assert 'Revenue this month:   0.00' in output


def test_report_counts_active_subscriptions(active_subscription):
    assert 'Active subscriptions: 1' in _report()


def test_report_sums_this_months_succeeded_payments(user):
    from apps.subscriptions.models import Payment

    Payment.objects.create(
        user=user, stripe_payment_intent_id='pi_1', amount='10.00', status='succeeded'
    )
    Payment.objects.create(
        user=user, stripe_payment_intent_id='pi_2', amount='5.00', status='succeeded'
    )
    # Failed payments are not revenue.
    Payment.objects.create(
        user=user, stripe_payment_intent_id='pi_3', amount='99.00', status='failed'
    )

    assert 'Revenue this month:   15.00' in _report()


def test_report_excludes_payments_from_previous_months(user):
    from apps.subscriptions.models import Payment

    payment = Payment.objects.create(
        user=user, stripe_payment_intent_id='pi_old', amount='50.00', status='succeeded'
    )
    # created_at is auto_now_add, so it has to be moved after the fact.
    last_month = timezone.now().replace(day=1) - timedelta(days=5)
    Payment.objects.filter(pk=payment.pk).update(created_at=last_month)

    assert 'Revenue this month:   0.00' in _report()


def test_report_counts_open_invoices(user):
    from apps.subscriptions.models import Invoice

    Invoice.objects.create(
        user=user, stripe_invoice_id='in_open', amount='1.00', status='open'
    )

    assert 'Open invoices:        1' in _report()
