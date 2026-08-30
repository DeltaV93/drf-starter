/**
 * The brand tokens, turned into a React Native Paper theme.
 *
 * The mobile counterpart of `website/src/styles/theme.ts`, and deliberately
 * the same shape of file: it derives everything from `@app/shared/brand` and
 * holds no literals of its own, so a re-brand stays one file for both clients.
 * If you find yourself wanting a colour here that is not in `brand.ts`, add it
 * there instead -- that is the whole arrangement.
 *
 * Paper is Material Design 3 and MUI is Material Design 2, so the mapping is
 * not one-to-one. MD3 asks for a `container` pair for each role (a muted
 * surface plus a colour to write on it) where MD2 asks for light/main/dark.
 * The derivations below are commented where the answer was a judgement rather
 * than a lookup.
 */

import {
  cardShadow,
  darkPalette,
  fontFamily,
  grey,
  lightPalette,
  shape,
  spacingUnit,
  typography,
  type BrandPalette,
} from '@app/shared/brand';
import { MD3DarkTheme, MD3LightTheme, type MD3Theme } from 'react-native-paper';

/** What this project adds to Paper's theme, available through `useTheme`. */
export interface AppTheme extends MD3Theme {
  spacing: (multiplier?: number) => number;
  radius: typeof shape;
  cardShadow: string;
}

/**
 * Read any colour the brand might hold into RGB.
 *
 * The default tokens are hex, but `text.*` is already `rgba(...)` and nothing
 * stops a project using that form for a brand colour too.
 */
function toRgb(color: string): [number, number, number] | null {
  const hex = color.trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hex) {
    const value = hex[1].length === 3 ? [...hex[1]].map((c) => c + c).join('') : hex[1];
    return [
      parseInt(value.slice(0, 2), 16),
      parseInt(value.slice(2, 4), 16),
      parseInt(value.slice(4, 6), 16),
    ];
  }

  const functional = color.match(/^rgba?\(([^)]+)\)$/i);
  if (functional) {
    const parts = functional[1].split(',').map((n) => parseFloat(n));
    if (parts.length >= 3 && parts.every((n) => !Number.isNaN(n))) {
      return [parts[0], parts[1], parts[2]];
    }
  }

  return null;
}

/**
 * `amount` of `color` over `onto`.
 *
 * This is what makes an MD3 "container" a container. The first version of
 * this file mapped `primaryContainer` to the palette's `light` variant, which
 * is *brighter* than `main` -- so the informational banner on the profile
 * screen rendered as a saturated block of cyan rather than the pale tint the
 * role is for. It looked like an error state.
 *
 * A container is a low-chroma wash of the role colour over the surface, so
 * that is what this computes. Still derived entirely from the brand: no new
 * colour is named, one is mixed.
 */
function mix(color: string, onto: string, amount: number): string {
  const a = toRgb(color);
  const b = toRgb(onto);
  // Unparseable input falls back to the role colour rather than to something
  // invented, so an unusual palette degrades to "too saturated" rather than
  // to a colour with no relationship to the brand.
  if (!a || !b) return color;

  const channel = (i: number) => Math.round(a[i] * amount + b[i] * (1 - amount));
  return `rgb(${channel(0)}, ${channel(1)}, ${channel(2)})`;
}

function colorsFor(palette: BrandPalette, base: MD3Theme, dark: boolean) {
  // How much of the role colour survives into its container. Dark mode needs
  // more, because a wash this faint over near-black is invisible.
  const TINT = dark ? 0.28 : 0.14;
  const surface = palette.background.paper;

  /** The container pair for a role: a wash, and something readable on it. */
  const container = (role: BrandPalette['primary']) => ({
    fill: mix(role.main, surface, TINT),
    // On a pale wash the darker variant reads; on a dark one the lighter.
    on: dark ? role.light : role.dark,
  });

  return {
    ...base.colors,

    primary: palette.primary.main,
    onPrimary: palette.primary.contrastText,
    // MD3's container roles are a muted fill plus something readable on it.
    // The brand has no such pair, so `container()` mixes one -- see the note
    // there for why the obvious choice was wrong.
    primaryContainer: container(palette.primary).fill,
    onPrimaryContainer: container(palette.primary).on,

    secondary: palette.secondary.main,
    onSecondary: palette.secondary.contrastText,
    secondaryContainer: container(palette.secondary).fill,
    onSecondaryContainer: container(palette.secondary).on,

    // MD3 has a third accent that MD2 does not. Mapping it to `info` rather
    // than inventing one keeps every colour on screen traceable to a token.
    tertiary: palette.info.main,
    onTertiary: palette.info.contrastText,
    tertiaryContainer: container(palette.info).fill,
    onTertiaryContainer: container(palette.info).on,

    error: palette.error.main,
    onError: palette.error.contrastText,
    errorContainer: container(palette.error).fill,
    onErrorContainer: container(palette.error).on,

    background: palette.background.default,
    onBackground: palette.text.primary,
    surface: palette.background.paper,
    onSurface: palette.text.primary,

    // The quieter surface behind chips, dividers and inactive controls.
    surfaceVariant: dark ? grey[800] : grey[100],
    onSurfaceVariant: palette.text.secondary,
    outline: dark ? grey[600] : grey[400],
    outlineVariant: dark ? grey[700] : grey[300],

    surfaceDisabled: palette.text.disabled,
    onSurfaceDisabled: palette.text.disabled,

    // Paper tints elevated surfaces by blending the primary into the surface.
    // With one flat brand surface the tint is what stops a card from
    // disappearing into the page, so the levels are kept rather than flattened.
    elevation: base.colors.elevation,
  };
}

/**
 * Paper's type scale, restated in the brand's family and sizes.
 *
 * MD3 names its roles by size and prominence (`headlineLarge`) where the web
 * scale names them by document structure (`h1`). They are lined up below in
 * the order a reader would expect, so a change to the shared scale moves both
 * clients together.
 *
 * Sizes are numbers here rather than `rem`: React Native has no root font
 * size to be relative to. The system text-size setting is honoured by
 * `allowFontScaling`, which is on by default -- do not switch it off.
 */
function fontsFor(base: MD3Theme['fonts']): MD3Theme['fonts'] {
  const family = { fontFamily };
  const size = (rem: string) => Math.round(parseFloat(rem) * 16);

  return {
    ...base,
    displayLarge: { ...base.displayLarge, ...family, fontSize: size(typography.h1.fontSize) },
    displayMedium: { ...base.displayMedium, ...family, fontSize: size(typography.h2.fontSize) },
    displaySmall: { ...base.displaySmall, ...family, fontSize: size(typography.h3.fontSize) },
    headlineLarge: { ...base.headlineLarge, ...family, fontSize: size(typography.h3.fontSize) },
    headlineMedium: {
      ...base.headlineMedium,
      ...family,
      fontSize: size(typography.h4.fontSize),
    },
    headlineSmall: { ...base.headlineSmall, ...family, fontSize: size(typography.h5.fontSize) },
    titleLarge: { ...base.titleLarge, ...family, fontSize: size(typography.h5.fontSize) },
    titleMedium: { ...base.titleMedium, ...family, fontSize: size(typography.h6.fontSize) },
    titleSmall: { ...base.titleSmall, ...family, fontSize: size(typography.subtitle2.fontSize) },
    bodyLarge: { ...base.bodyLarge, ...family, fontSize: size(typography.body1.fontSize) },
    bodyMedium: { ...base.bodyMedium, ...family, fontSize: size(typography.body2.fontSize) },
    bodySmall: { ...base.bodySmall, ...family, fontSize: size(typography.caption.fontSize) },
    labelLarge: { ...base.labelLarge, ...family, fontSize: size(typography.button.fontSize) },
    labelMedium: { ...base.labelMedium, ...family, fontSize: size(typography.caption.fontSize) },
    labelSmall: { ...base.labelSmall, ...family, fontSize: size(typography.overline.fontSize) },
    default: { ...base.default, ...family },
  };
}

const shared = {
  // Paper scales its own components from one number, the way MUI does from
  // `shape.borderRadius`. The named radii are on the theme as well, for the
  // components that opt out.
  roundness: shape.base,
  radius: shape,
  cardShadow,
  spacing: (multiplier = 1) => spacingUnit * multiplier,
};

export const lightTheme: AppTheme = {
  ...MD3LightTheme,
  ...shared,
  colors: colorsFor(lightPalette, MD3LightTheme, false),
  fonts: fontsFor(MD3LightTheme.fonts),
};

export const darkTheme: AppTheme = {
  ...MD3DarkTheme,
  ...shared,
  colors: colorsFor(darkPalette, MD3DarkTheme, true),
  fonts: fontsFor(MD3DarkTheme.fonts),
};
