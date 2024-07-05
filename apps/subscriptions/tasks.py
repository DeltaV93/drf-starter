from celery import shared_task
from django.core.mail import send_mail
from .models import Invoice
from utils.logging_utils import get_logger, log_exception, timed_function

logger = get_logger(__name__)


@shared_task
@log_exception(logger)
@timed_function(logger)
def generate_invoice_pdf(invoice_id):
    invoice = Invoice.objects.get(id=invoice_id)
    # Implement custom PDF generation logic here
    pdf_url = "https://example.com/invoices/123.pdf"  # Replace with actual URL
    invoice.pdf_url = pdf_url
    invoice.save()

    logger.info(f"Generated PDF invoice for invoice {invoice_id}")

    # Send email with PDF link
    send_mail(
        'Your invoice is ready',
        f'You can download your invoice here: {pdf_url}',
        'from@example.com',
        [invoice.user.email],
        fail_silently=False,
    )

    logger.info(f"Sent invoice email for invoice {invoice_id}")

# Call this task as:
# generate_invoice_pdf.delay(invoice.id)