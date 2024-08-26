from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from rest_framework.authentication import SessionAuthentication, TokenAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated

from utils.api_utils import api_response
from utils.logging_utils import get_logger, RequestLogger
from .models import SubscriptionPlan, AddOn
from .services import StripeService

logger = get_logger(__name__)
request_logger = RequestLogger(logger)


class SubscribeView(LoginRequiredMixin, View):
    """
    View for handling subscription requests to a specific plan.

    This view creates a Stripe checkout session for the authenticated user
    based on the selected subscription plan. It requires user authentication.

    Methods:
    - post: Handles POST requests to initiate the subscription process.

    URL Parameters:
    - plan_id: The ID of the SubscriptionPlan to subscribe to.

    Returns:
    - JSON response containing the Stripe checkout session ID.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    # permission_classes = [IsAuthenticated]

    def post(self, request, stripe_price_id):
        print(f"User authenticated: {request.user.is_authenticated}")
        print(f"User: {request.user}")
        print("setting subscription plan")
        request_logger.log_request(request)
        print("got the user")
        plan = SubscriptionPlan.objects.get(stripe_price_id=stripe_price_id)
        print("Got the plan: {}".format(plan))
        checkout_session_id = StripeService.create_checkout_session(request.user, plan)
        print("checkout session id: {}".format(checkout_session_id))
        response = api_response(data={'checkout_session_id': checkout_session_id})
        request_logger.log_response(response, request)
        return response


class AddAddonView(LoginRequiredMixin, View):
    """
    View for adding an add-on to a user's existing subscription.

    This view handles the process of adding a specific add-on to the
    authenticated user's current subscription. It requires user authentication.

    Methods:
    - post: Handles POST requests to add the specified add-on.

    URL Parameters:
    - addon_id: The ID of the AddOn to be added to the subscription.

    Returns:
    - JSON response confirming the successful addition of the add-on.
    """

    def post(self, request, addon_id):
        request_logger.log_request(request)
        addon = AddOn.objects.get(id=addon_id)
        StripeService.add_addon(request.user, addon)
        response = api_response(message="Add-on successfully added to your subscription.")
        request_logger.log_response(response, request)
        return response


 # @method_decorator(csrf_exempt, name='dispatch')
class WebhookView(View):
    """
    View for handling Stripe webhook events.

    This view processes incoming webhook events from Stripe,
    allowing the application to respond to events such as successful payments,
    subscription updates, etc.

    Methods:
    - post: Handles POST requests from Stripe's webhook.

    Note:
    This view does not require authentication as it's accessed by Stripe's servers.

    Returns:
    - HTTP response with status 200 if the webhook was processed successfully,
      or status 400 if there was an error.
    """

    def post(self, request):
        request_logger.log_request(request)
        payload = request.body
        sig_header = request.META['HTTP_STRIPE_SIGNATURE']
        success = StripeService.process_webhook(payload, sig_header)
        response = api_response(status=200 if success else 400)
        request_logger.log_response(response, request)
        return response
