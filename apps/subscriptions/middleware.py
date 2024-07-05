from django.utils import timezone
from .models import Subscription

class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                subscription = Subscription.objects.get(user=request.user)
                grace_period = timezone.now() + timezone.timedelta(days=14)
                if subscription.status != 'active' and subscription.current_period_end < grace_period:
                    request.subscription_expired = True
            except Subscription.DoesNotExist:
                request.subscription_expired = True

        response = self.get_response(request)
        return response