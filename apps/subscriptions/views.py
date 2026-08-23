from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from utils.api_utils import api_response
from utils.logging_utils import get_logger

from .models import AddOn, Subscription, SubscriptionPlan
from .serializers import AddOnSerializer, SubscriptionPlanSerializer, SubscriptionSerializer
from .services import StripeService

logger = get_logger(__name__)


class PlanListView(APIView):
    """List the plans a visitor can subscribe to."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary='List subscription plans',
        responses={200: SubscriptionPlanSerializer(many=True)},
    )
    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True)
        return api_response(
            data=SubscriptionPlanSerializer(plans, many=True).data,
            message='Plans retrieved.',
        )


class MySubscriptionView(APIView):
    """The authenticated user's current subscription, if any."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get the current subscription', responses={200: SubscriptionSerializer}
    )
    def get(self, request):
        subscription = (
            Subscription.objects.filter(user=request.user).select_related('plan').first()
        )
        return api_response(
            data=SubscriptionSerializer(subscription).data if subscription else None,
            message='Subscription retrieved.' if subscription else 'No active subscription.',
        )


class SubscribeView(APIView):
    """Create a Stripe checkout session for a plan.

    Returns the session id; the frontend hands it to Stripe.js to redirect.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Start checkout for a plan', request=None, responses={200: None})
    def post(self, request, stripe_price_id):
        plan = SubscriptionPlan.objects.filter(
            stripe_price_id=stripe_price_id, is_active=True
        ).first()
        if plan is None:
            return api_response(message='No such plan.', status_code=status.HTTP_404_NOT_FOUND)

        session = StripeService.create_checkout_session(request.user, plan)
        return api_response(
            data={
                'checkout_session_id': session['session_id'],
                'checkout_url': session['url'],
            },
            message='Checkout session created.',
        )


class AddAddonView(APIView):
    """Attach an add-on to the caller's existing subscription."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Add an add-on', request=None, responses={200: AddOnSerializer})
    def post(self, request, addon_id):
        add_on = AddOn.objects.filter(pk=addon_id, is_active=True).first()
        if add_on is None:
            return api_response(
                message='No such add-on.', status_code=status.HTTP_404_NOT_FOUND
            )

        if not Subscription.objects.filter(user=request.user).exists():
            return api_response(
                message='You need an active subscription before adding add-ons.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        StripeService.add_addon(request.user, add_on)
        return api_response(
            data=AddOnSerializer(add_on).data,
            message='Add-on added to your subscription.',
        )


class CancelSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Cancel the current subscription',
        request=None,
        responses={200: SubscriptionSerializer},
    )
    def post(self, request):
        if not Subscription.objects.filter(user=request.user).exists():
            return api_response(
                message='You do not have a subscription to cancel.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        subscription = StripeService.cancel_subscription(request.user)
        return api_response(
            data=SubscriptionSerializer(subscription).data,
            message='Subscription will end at the close of the current period.',
        )


# Stripe signs its callbacks and has no CSRF token, so this one endpoint opts
# out of CSRF. The signature check in process_webhook is what authenticates it.
@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(APIView):
    """Receive Stripe webhook events."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(summary='Stripe webhook receiver', request=None, responses={200: None})
    def post(self, request):
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        if not sig_header:
            logger.warning('Stripe webhook received without a signature header')
            return api_response(
                message='Missing signature.', status_code=status.HTTP_400_BAD_REQUEST
            )

        handled = StripeService.process_webhook(request.body, sig_header)
        return api_response(
            message='Webhook processed.' if handled else 'Webhook rejected.',
            status_code=status.HTTP_200_OK if handled else status.HTTP_400_BAD_REQUEST,
        )
