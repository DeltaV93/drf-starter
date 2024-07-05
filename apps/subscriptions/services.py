import stripe
from django.conf import settings
from .models import Subscription, UserAddOn, Invoice, Payment
from utils.logging_utils import get_logger, log_exception, timed_function, sanitize_log_data

logger = get_logger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    @staticmethod
    @log_exception(logger)
    @timed_function(logger)
    def create_checkout_session(user, plan):
        try:
            session = stripe.checkout.Session.create(
                customer_email=user.email,
                payment_method_types=['card', 'apple_pay', 'google_pay'],
                line_items=[{
                    'price': plan.stripe_price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=settings.STRIPE_SUCCESS_URL,
                cancel_url=settings.STRIPE_CANCEL_URL,
            )
            logger.info(f"Checkout session created for user {user.id}")
            return session.id
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error in create_checkout_session: {str(e)}")
            raise

    @staticmethod
    @log_exception(logger)
    @timed_function(logger)
    def create_subscription(user, plan):
        try:
            stripe_customer = stripe.Customer.create(email=user.email)
            stripe_subscription = stripe.Subscription.create(
                customer=stripe_customer.id,
                items=[{'price': plan.stripe_price_id}],
            )
            subscription = Subscription.objects.create(
                user=user,
                plan=plan,
                stripe_subscription_id=stripe_subscription.id,
                status=stripe_subscription.status,
                current_period_end=timezone.datetime.fromtimestamp(stripe_subscription.current_period_end),
            )
            logger.info(f"Subscription created for user {user.id}")
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error in create_subscription: {str(e)}")
            raise

    @staticmethod
    @log_exception(logger)
    @timed_function(logger)
    def add_addon(user, add_on):
        try:
            subscription = Subscription.objects.get(user=user)
            stripe_subscription_item = stripe.SubscriptionItem.create(
                subscription=subscription.stripe_subscription_id,
                price=add_on.stripe_price_id,
            )
            UserAddOn.objects.create(
                user=user,
                add_on=add_on,
                stripe_subscription_item_id=stripe_subscription_item.id,
            )
            logger.info(f"Add-on {add_on.id} added for user {user.id}")
            return user_addon
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error in add_addon: {str(e)}")
            raise

    @staticmethod
    @log_exception(logger)
    @timed_function(logger)
    def generate_invoice_pdf(invoice_id):
        invoice = Invoice.objects.get(id=invoice_id)
        # Implement custom PDF generation logic here
        pdf_url = "https://example.com/invoices/123.pdf"  # Replace with actual URL
        invoice.pdf_url = pdf_url
        invoice.save()

        # Send email with PDF link
        send_mail(
            'Your invoice is ready',
            f'You can download your invoice here: {pdf_url}',
            'from@example.com',
            [invoice.user.email],
            fail_silently=False,
        )
    @staticmethod
    def process_webhook(payload, sig_header):
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error(f"Invalid payload in Stripe webhook: {str(e)}")
            return False
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature in Stripe webhook: {str(e)}")
            return False

        logger.info(f"Processing Stripe webhook event: {event.type}")

        if event.type == 'invoice.paid':
            # Handle successful payment
            pass
        elif event.type == 'invoice.payment_failed':
            # Handle failed payment
            pass
        elif event.type == 'customer.subscription.updated':
            # Handle subscription updates
            pass

        return True