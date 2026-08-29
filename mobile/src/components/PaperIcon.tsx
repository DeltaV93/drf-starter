/**
 * Where Paper gets its icons from.
 *
 * React Native Paper renders icons through `react-native-vector-icons`, which
 * an Expo project does not have -- Expo ships `@expo/vector-icons` instead.
 * Left unconfigured, every icon in the app silently renders as nothing: no
 * error, no placeholder, just buttons and list rows with a gap where the icon
 * should be.
 *
 * Passing this to `PaperProvider` as `settings.icon` is the documented fix,
 * and it is the only place the two libraries have to be introduced.
 */

import MaterialCommunityIcons from '@expo/vector-icons/MaterialCommunityIcons';
import type { ComponentProps } from 'react';

type IconName = ComponentProps<typeof MaterialCommunityIcons>['name'];

interface PaperIconProps {
  name: string;
  /** Paper leaves this out where the icon should inherit its surface's tint. */
  color?: string;
  size: number;
  direction?: 'rtl' | 'ltr';
}

export function PaperIcon({ name, color, size }: PaperIconProps) {
  // Paper types its icon names as a bare string, and the icon set types its
  // own as a union. Every name Paper passes comes from the same Material
  // Community set, so the cast is describing that rather than papering over
  // a mismatch.
  return <MaterialCommunityIcons name={name as IconName} color={color} size={size} />;
}
