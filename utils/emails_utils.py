import logging
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def send_email(subject, template_name, context, recipient_list, from_email=None):
    """
    Send an email using a template.

    :param subject: Email subject
    :param template_name: Name of the HTML template to use
    :param context: Dictionary containing context for the template
    :param recipient_list: List of recipient email addresses
    :param from_email: Sender's email address (optional)
    """
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)

    try:
        msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Email sent successfully to {', '.join(recipient_list)}")
    except Exception as e:
        logger.error(f"Failed to send email to {', '.join(recipient_list)}: {str(e)}")
        raise


def send_password_reset_email(user, reset_url):
    subject = "Password Reset Request"
    template_name = "email/password_reset.html"
    context = {
        "user": user,
        "reset_url": reset_url
    }
    recipient_list = [user.email]

    try:
        send_email(subject, template_name, context, recipient_list)
        logger.info(f"Password reset email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")