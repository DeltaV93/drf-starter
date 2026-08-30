/**
 * What a screen shows when its feature is switched off.
 *
 * Four screens need this and each was writing its own sentence naming its own
 * two flags. One component, two interpolated names: the phrasing is
 * translated once and the flag names stay exact, which is the only part
 * anyone reading it actually needs.
 *
 * The route still exists when the flag is off -- an emailed invitation has to
 * keep resolving -- so this is what stands in for the screen rather than a
 * 404.
 */

import { useTranslation } from 'react-i18next';

import { Screen, ScreenHeader } from './Screen';

interface FeatureOffProps {
  /** The feature's own name, already translated. */
  feature: string;
  /** The EXPO_PUBLIC_ flag this client reads. */
  clientFlag: string;
  /** The flag the backend reads. Both have to agree. */
  serverFlag: string;
}

export function FeatureOff({ feature, clientFlag, serverFlag }: FeatureOffProps) {
  const { t } = useTranslation();

  return (
    <Screen>
      <ScreenHeader
        title={t('featureOff', { feature })}
        subtitle={t('featureOffHelp', { clientFlag, serverFlag })}
      />
    </Screen>
  );
}
