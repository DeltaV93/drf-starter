/**
 * The frame every screen sits in.
 *
 * Three things that are easy to get wrong once per screen instead of right
 * once here: the safe-area inset (a title under the notch), the keyboard
 * (a text field the keyboard covers, on a form the user cannot then submit),
 * and the background colour when the theme changes.
 */

import type { ReactNode } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import { ActivityIndicator, Text, useTheme } from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { AppTheme } from '../theme/paper';

interface ScreenProps {
  /** Optional because a screen showing its spinner has nothing to render. */
  children?: ReactNode;
  /** Turn off for a screen that manages its own scrolling, such as a list. */
  scrollable?: boolean;
  loading?: boolean;
  contentStyle?: StyleProp<ViewStyle>;
  /**
   * Pull down to reload. Omit it and the gesture does nothing, which is what
   * a screen with nothing to reload should do.
   *
   * Here rather than per screen because every list wanted the same six lines,
   * and because the tint has to come from the theme -- the default spinner is
   * grey on both platforms and looks like a rendering artefact against a
   * brand colour.
   */
  onRefresh?: () => void;
  refreshing?: boolean;
}

export function Screen({
  children,
  scrollable = true,
  loading,
  contentStyle,
  onRefresh,
  refreshing = false,
}: ScreenProps) {
  const theme = useTheme<AppTheme>();
  const insets = useSafeAreaInsets();

  const padding = {
    paddingHorizontal: theme.spacing(2),
    paddingTop: theme.spacing(2),
    // The inset, not a constant. A phone with a home indicator needs the
    // space; one with a physical button does not, and hardcoding either
    // leaves a gap on half the devices in the world.
    paddingBottom: insets.bottom + theme.spacing(2),
  };

  const body = loading ? (
    <View style={styles.centered}>
      <ActivityIndicator accessibilityLabel="Loading" />
    </View>
  ) : (
    children
  );

  return (
    <KeyboardAvoidingView
      style={[styles.fill, { backgroundColor: theme.colors.background }]}
      // iOS moves the whole view; Android resizes it, and applying iOS's
      // behaviour there pushes the content off the top of the screen.
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      {scrollable ? (
        <ScrollView
          contentContainerStyle={[padding, contentStyle]}
          keyboardShouldPersistTaps="handled"
          refreshControl={
            onRefresh ? (
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor={theme.colors.primary}
                colors={[theme.colors.primary]}
              />
            ) : undefined
          }
        >
          {body}
        </ScrollView>
      ) : (
        <View style={[styles.fill, padding, contentStyle]}>{body}</View>
      )}
    </KeyboardAvoidingView>
  );
}

/** A heading and optional explanation, spaced consistently. */
export function ScreenHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  const theme = useTheme<AppTheme>();

  return (
    <View style={{ marginBottom: theme.spacing(3) }}>
      {/* Announced as a heading, so a screen reader's heading navigation
          finds it and someone landing on the screen hears what it is rather
          than the first button on it. */}
      <Text variant="headlineMedium" accessibilityRole="header">
        {title}
      </Text>
      {subtitle ? (
        <Text
          variant="bodyMedium"
          style={{ marginTop: theme.spacing(1), color: theme.colors.onSurfaceVariant }}
        >
          {subtitle}
        </Text>
      ) : null}
    </View>
  );
}

/** What a list shows when there is nothing in it. */
export function EmptyState({ message }: { message: string }) {
  const theme = useTheme<AppTheme>();

  return (
    // A live region: this replaces a list that was loading, and without the
    // announcement a screen-reader user is left on a screen that has gone
    // quiet with no way to tell whether it finished or stalled.
    <View
      accessibilityLiveRegion="polite"
      style={[styles.centered, { padding: theme.spacing(4) }]}
    >
      <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
        {message}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', minHeight: 120 },
});
