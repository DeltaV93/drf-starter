import pytest
from django.core import mail

pytestmark = pytest.mark.django_db


@pytest.fixture
def invoice(db, user):
    from apps.subscriptions.models import Invoice

    return Invoice.objects.create(
        user=user,
        stripe_invoice_id='in_123',
        amount='19.99',
        status='paid',
        pdf_url='https://stripe.example/in_123.pdf',
    )


def test_email_invoice_sends_the_pdf_link(invoice):
    from apps.subscriptions.tasks import email_invoice

    assert email_invoice(invoice.pk) is True
    assert len(mail.outbox) == 1
    assert invoice.pdf_url in mail.outbox[0].alternatives[0][0]


def test_email_invoice_skips_an_invoice_with_no_pdf(invoice):
    from apps.subscriptions.tasks import email_invoice

    invoice.pdf_url = ''
    invoice.save(update_fields=['pdf_url'])

    assert email_invoice(invoice.pk) is False
    assert mail.outbox == []


def test_email_invoice_handles_a_missing_invoice():
    from apps.subscriptions.tasks import email_invoice

    assert email_invoice(999999) is False
