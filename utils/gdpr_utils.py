import uuid
from django.utils import timezone

def anonymize_user_data(user):
    """
    Anonymize user data in compliance with GDPR.

    This function replaces personal information with anonymous data and
    deactivates the user account.

    :param user: The User object to be anonymized
    """
    # Generate a unique identifier
    unique_id = uuid.uuid4().hex[:10]

    # Anonymize personal data
    user.username = f"deleted_user_{unique_id}"
    user.email = f"{unique_id}@deleted.com"
    user.first_name = "Deleted"
    user.last_name = "User"

    # Clear any other personal data fields
    # Add any additional fields your User model might have
    user.phone_number = ""  # If you have this field

    # Deactivate the account
    user.is_active = False

    # Set deletion timestamp
    user.date_deleted = timezone.now()  # Assuming you've added this field to your User model

    # Save the changes
    user.save()