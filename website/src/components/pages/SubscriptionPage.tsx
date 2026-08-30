import {
  Alert,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  CircularProgress,
  Container,
  Typography,
} from '@mui/material';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ApiError, apiCall } from '../../lib/api';
import { routes } from '../../lib/routes';
import type { SubscriptionPlan } from '@app/shared/types';
import { useToast } from '../../store/toast';

const BILLING_ENABLED = import.meta.env.VITE_STRIPE_ENABLED === 'true';

export default function SubscriptionPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const [plans, setPlans] = useState<SubscriptionPlan[] | null>(null);
  const [pendingPriceId, setPendingPriceId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const envelope = await apiCall<SubscriptionPlan[]>({
          url: routes.api.billing.plans(),
          method: 'GET',
        });
        if (!cancelled) setPlans(envelope.data ?? []);
      } catch (error) {
        if (cancelled) return;
        setPlans([]);
        setLoadError(error instanceof ApiError ? error.message : t('genericError'));
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [t]);

  const subscribe = useCallback(
    async (plan: SubscriptionPlan) => {
      setPendingPriceId(plan.stripe_price_id);
      try {
        // The backend creates the Checkout session; card details are entered
        // on Stripe's own hosted page, so they never touch this app.
        const envelope = await apiCall<{ checkout_session_id: string; checkout_url: string }>({
          url: routes.api.billing.subscribe(plan.stripe_price_id),
          method: 'POST',
          errorMessage: t('subscriptionError'),
        });

        const checkoutUrl = envelope.data?.checkout_url;
        if (!checkoutUrl) throw new ApiError(t('subscriptionError'));

        // stripe.js dropped redirectToCheckout; navigating to the session's
        // hosted URL is the supported way in.
        window.location.assign(checkoutUrl);
      } catch (error) {
        toast.error(error instanceof ApiError ? error.message : t('genericError'));
        setPendingPriceId(null);
      }
    },
    [t, toast],
  );

  if (plans === null) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 8, mb: 4 }}>
        <Typography variant="h4" align="center" gutterBottom>
          {t('selectSubscription')}
        </Typography>

        {loadError && <Alert severity="error" sx={{ mb: 3 }}>{loadError}</Alert>}

        {!BILLING_ENABLED && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            {t('stripeNotConfigured')}
          </Alert>
        )}

        {plans.length === 0 && !loadError && (
          <Alert severity="info">{t('noPlansAvailable')}</Alert>
        )}

        <Box
          sx={{
            display: 'grid',
            gap: 3,
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' },
          }}
        >
          {plans.map((plan) => (
            <Card key={plan.id} sx={{ display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Typography variant="h5" component="div" gutterBottom>
                  {plan.name}
                </Typography>
                <Typography variant="h4" color="primary" gutterBottom>
                  {t('pricePerMonth', { price: plan.price })}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('seatsIncluded', { count: plan.user_limit })}
                </Typography>
              </CardContent>
              <CardActions>
                <Button
                  variant="contained"
                  fullWidth
                  disabled={pendingPriceId !== null || !BILLING_ENABLED}
                  onClick={() => subscribe(plan)}
                >
                  {pendingPriceId === plan.stripe_price_id ? t('redirecting') : t('selectPlan')}
                </Button>
              </CardActions>
            </Card>
          ))}
        </Box>
      </Box>
    </Container>
  );
}
