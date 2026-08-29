/**
 * Your plan. Read-only, and that is a rule rather than an omission.
 *
 * Apple's guidelines require digital goods and subscriptions consumed inside
 * an app to be sold through in-app purchase. A Stripe checkout reached from
 * here -- in a web view, an external browser, or anything else -- is grounds
 * for rejection, and so is a button whose only purpose is to point at one.
 *
 * So this screen shows the state and stops. Changing a plan happens on the
 * website, where the same account and the same Stripe customer are waiting.
 *
 * If you are selling something the rules exempt -- physical goods, or a B2B
 * service bought outside the app -- a purchase flow is legitimate; add it
 * knowingly. If you are selling ordinary consumer software, adding in-app
 * purchase means an entitlement model the backend does not have yet. Either
 * way it is a decision, not an oversight. `docs/mobile.md` has the detail.
 */

import { useEffect, useState } from 'react';
import { View } from 'react-native';
import { ActivityIndicator, Card, Divider, List, Text, useTheme } from 'react-native-paper';

import type { Subscription } from '@app/shared/types';

import { Screen, ScreenHeader } from '../../components/Screen';
import { flags, WEB_URL } from '../../lib/config';
import { apiData } from '../../lib/api';
import { routes } from '../../lib/routes';
import type { AppTheme } from '../../theme/paper';

type State = { status: 'loading' } | { status: 'ready'; subscription: Subscription | null };

export default function SubscriptionScreen() {
  const theme = useTheme<AppTheme>();
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    if (!flags.billing) return;
    let cancelled = false;

    apiData<Subscription>({ url: routes.api.billing.subscription() })
      .then((subscription) => {
        if (!cancelled) setState({ status: 'ready', subscription: subscription ?? null });
      })
      .catch(() => {
        // No subscription is the ordinary state for a free account, and the
        // endpoint answers 404 for it. Not an error worth a red banner.
        if (!cancelled) setState({ status: 'ready', subscription: null });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (!flags.billing) {
    return (
      <Screen>
        <ScreenHeader
          title="Billing is off"
          subtitle="Set EXPO_PUBLIC_STRIPE_ENABLED, and STRIPE_ENABLED on the backend."
        />
      </Screen>
    );
  }

  if (state.status === 'loading') {
    return (
      <Screen>
        <ActivityIndicator accessibilityLabel="Loading" />
      </Screen>
    );
  }

  const { subscription } = state;

  return (
    <Screen>
      <ScreenHeader title="Subscription" />

      <Card mode="outlined">
        <Card.Content>
          {subscription ? (
            <>
              <Text variant="titleLarge">{subscription.plan.name}</Text>
              <Divider style={{ marginVertical: theme.spacing(1) }} />
              <List.Item title="Status" description={subscription.status} />
              <List.Item
                title="Renews"
                description={new Date(subscription.current_period_end).toLocaleDateString()}
              />
              <List.Item title="Price" description={subscription.plan.price} />
            </>
          ) : (
            <>
              <Text variant="titleLarge">No plan</Text>
              <Text style={{ marginTop: theme.spacing(1) }}>
                This account is not subscribed.
              </Text>
            </>
          )}
        </Card.Content>
      </Card>

      <View style={{ marginTop: theme.spacing(3) }}>
        <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
          Plans are managed on the website
          {WEB_URL ? `, at ${WEB_URL}` : ''}. Sign in there with this same
          account.
        </Text>
      </View>
    </Screen>
  );
}
