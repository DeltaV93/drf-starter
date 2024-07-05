from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import SubscriptionPlan, Subscription
from .services import StripeService
from unittest.mock import patch

User = get_user_model()


class SubscriptionTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='testpass123')
        self.plan = SubscriptionPlan.objects.create(name='Basic', stripe_price_id='price_123', user_limit=10,
                                                    price=9.99)

    @patch('stripe.Subscription.create')
    def test_create_subscription(self, mock_stripe_sub_create):
        mock_stripe_sub_create.return_value = type('obj', (object,), {
            'id': 'sub_123',
            'status': 'active',
            'current_period_end': 1609459200,
        })

        StripeService.create_subscription(self.user, self.plan)
        subscription = Subscription.objects.get(user=self.user)

        self.assertEqual(subscription.stripe_subscription_id, 'sub_123')
        self.assertEqual(subscription.status, 'active')
        self.assertEqual(subscription.plan, self.plan)