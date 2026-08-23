from celery import shared_task

from utils.emails_utils import send_email
from utils.logging_utils import get_logger, log_exception

from .models import Invoice

logger = get_logger(__name__)


@shared_task
@log_exception(logger)
def email_invoice(invoice_id):
    """Email a user the link to an invoice PDF.

    Stripe already hosts a PDF for every invoice and stores its URL on
    Invoice.pdf_url when the invoice.paid webhook arrives, so there is no PDF
    generation to do here. Swap in your own renderer if you need branded
    invoices.

    Call with: email_invoice.delay(invoice.id)
    """
    invoice = Invoice.objects.select_related('user').filter(pk=invoice_id).first()
    if invoice is None:
        logger.warning('email_invoice called for missing invoice %s', invoice_id)
        return False

    if not invoice.pdf_url:
        logger.warning('Invoice %s has no PDF url yet; not sending.', invoice_id)
        return False

    sent = send_email(
        subject='Your invoice is ready',
        template_name='emails/invoice_ready.html',
        context={'user': invoice.user, 'invoice': invoice},
        recipient_list=[invoice.user.email],
    )
    if sent:
        logger.info('Sent invoice email for invoice %s', invoice_id)
    return sent
