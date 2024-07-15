import logging
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import boto3
from botocore.exceptions import ClientError

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
        # Create a new SES resource and specify a region.
        client = boto3.client('ses', region_name=settings.AWS_SES_REGION_NAME)

        response = client.send_email(
            Destination={
                'ToAddresses': recipient_list,
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': 'UTF-8',
                        'Data': html_content,
                    },
                    'Text': {
                        'Charset': 'UTF-8',
                        'Data': text_content,
                    },
                },
                'Subject': {
                    'Charset': 'UTF-8',
                    'Data': subject,
                },
            },
            Source=from_email,
        )
    except ClientError as e:
        logger.error(f"Failed to send email to {', '.join(recipient_list)}: {str(e)}")
        raise
    else:
        logger.info(f"Email sent successfully to {', '.join(recipient_list)}. Message ID: {response['MessageId']}")

def send_password_reset_email(user, reset_url):
    subject = "Password Reset Request"
    template_name = "password_reset.html"
    context = {
        "user": user,
        "reset_url": reset_url
    }
    recipient_list = [user.email]

    try:
        send_email(subject, template_name, context, recipient_list)
        logger.info(f"Password reset email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        return False
