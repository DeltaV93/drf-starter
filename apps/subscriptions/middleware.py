from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import Subscription


class SubscriptionMiddleware:
    """Annotate each request with the caller's subscription state.

    Sets ``request.subscription`` and ``request.subscription_expired``. It
    only annotates -- enforcement belongs in a permission class, so that
    public pages stay reachable without a subscription.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.subscription = None
        request.subscription_expired = False

        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            subscription = (
                Subscription.objects.filter(user=user).select_related('plan').first()
            )
            request.subscription = subscription
            request.subscription_expired = self._is_expired(subscription)

        return self.get_response(request)

    @staticmethod
    def _is_expired(subscription):
        """True once a lapsed subscription is past its grace period.

        A current subscription is never expired, whenever it renews. A lapsed
        one keeps working until grace_period_days after the period it had
        already paid for.
        """
        if subscription is None:
            return True

        if subscription.is_current:
            return False

        grace_days = getattr(settings, 'SUBSCRIPTION_GRACE_PERIOD_DAYS', 14)
        return timezone.now() > subscription.current_period_end + timedelta(days=grace_days)
