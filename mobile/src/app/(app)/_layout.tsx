/**
 * The signed-in area.
 *
 * A tab bar rather than the website's header nav, because the website's nav
 * has more destinations than a phone has room for. So the optional features
 * that each had their own page there are folded into Settings here, and only
 * the ones someone returns to repeatedly get a tab.
 *
 * Tabs appear according to the same flags the backend uses. A tab for a
 * feature that is switched off would render and then 404, exactly as it would
 * on the website.
 */

import MaterialCommunityIcons from '@expo/vector-icons/MaterialCommunityIcons';
import { Tabs } from 'expo-router';
import type { ColorValue } from 'react-native';
import { useTheme } from 'react-native-paper';

import { flags } from '../../lib/config';
import type { AppTheme } from '../../theme/paper';

type IconName = React.ComponentProps<typeof MaterialCommunityIcons>['name'];

function icon(name: IconName) {
  // `ColorValue`, not `string`: React Native's own colour type also covers
  // the opaque handles a platform colour resolves to, and the tab bar passes
  // whichever it has.
  return ({ color, size }: { color: ColorValue; size: number }) => (
    <MaterialCommunityIcons name={name} color={color} size={size} />
  );
}

export default function AppLayout() {
  const theme = useTheme<AppTheme>();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.onSurfaceVariant,
        tabBarStyle: { backgroundColor: theme.colors.surface },
        headerStyle: { backgroundColor: theme.colors.surface },
        headerTintColor: theme.colors.onSurface,
      }}
    >
      <Tabs.Screen
        name="profile"
        options={{ title: 'Profile', tabBarIcon: icon('account-circle-outline') }}
      />
      <Tabs.Screen
        name="organization"
        options={{
          title: 'Team',
          tabBarIcon: icon('account-group-outline'),
          // `href: null` keeps the route reachable by URL -- an emailed
          // invitation still lands on it -- while hiding the tab. Removing
          // the screen instead would 404 that link.
          href: flags.organizations ? undefined : null,
        }}
      />
      <Tabs.Screen
        name="files"
        options={{
          title: 'Files',
          tabBarIcon: icon('file-outline'),
          href: flags.uploads ? undefined : null,
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{ title: 'Settings', tabBarIcon: icon('cog-outline') }}
      />

      {/* Reached from Settings rather than from the tab bar. */}
      <Tabs.Screen name="security" options={{ title: 'Security', href: null }} />
      <Tabs.Screen name="connections" options={{ title: 'Connections', href: null }} />
      <Tabs.Screen name="subscription" options={{ title: 'Subscription', href: null }} />
    </Tabs>
  );
}
