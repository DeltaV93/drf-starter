from django.shortcuts import redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from utils.api_utils import api_response
from .models import SubscriptionPlan, AddOn
from .services import StripeService
from utils.logging_utils import get_logger, RequestLogger

logger = get_logger(__name__)
request_logger = RequestLogger(logger)

class SubscribeView(LoginRequiredMixin, View):
    def post(self, request, plan_id):
        request_logger.log_request(request)
        plan = SubscriptionPlan.objects.get(id=plan_id)
        checkout_session_id = StripeService.create_checkout_session(request.user, plan)
        response = api_response(data={'checkout_session_id': checkout_session_id})
        request_logger.log_response(response, request)
        return response

class AddAddonView(LoginRequiredMixin, View):
    def post(self, request, addon_id):
        request_logger.log_request(request)
        addon = AddOn.objects.get(id=addon_id)
        StripeService.add_addon(request.user, addon)
        response = api_response(message="Add-on successfully added to your subscription.")
        request_logger.log_response(response, request)
        return response

class WebhookView(View):
    def post(self, request):
        request_logger.log_request(request)
        payload = request.body
        sig_header = request.META['HTTP_STRIPE_SIGNATURE']
        success = StripeService.process_webhook(payload, sig_header)
        response = api_response(status=200 if success else 400)
        request_logger.log_response(response, request)
        return response