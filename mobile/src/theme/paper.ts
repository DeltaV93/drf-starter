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

function colorsFor(palette: BrandPalette, base: MD3Theme, dark: boolean) {
  return {
    ...base.colors,

    primary: palette.primary.main,
    onPrimary: palette.primary.contrastText,
    // MD3's container roles are a muted fill plus text for it. The brand has
    // no such pair, so the fill comes from the scheme's quieter end -- `dark`
    // in dark mode, `light` in light mode -- which is the variant that reads
    // as a tint rather than as a second button.
    primaryContainer: dark ? palette.primary.dark : palette.primary.light,
    onPrimaryContainer: dark ? palette.primary.contrastText : palette.text.primary,

    secondary: palette.secondary.main,
    onSecondary: palette.secondary.contrastText,
    secondaryContainer: dark ? palette.secondary.dark : palette.secondary.light,
    onSecondaryContainer: dark ? palette.secondary.contrastText : palette.text.primary,

    // MD3 has a third accent that MD2 does not. Mapping it to `info` rather
    // than inventing one keeps every colour on screen traceable to a token.
    tertiary: palette.info.main,
    onTertiary: palette.info.contrastText,
    tertiaryContainer: dark ? palette.info.dark : palette.info.light,
    onTertiaryContainer: dark ? palette.info.contrastText : palette.text.primary,

    error: palette.error.main,
    onError: palette.error.contrastText,
    errorContainer: dark ? palette.error.dark : palette.error.light,
    onErrorContainer: dark ? palette.error.contrastText : palette.text.primary,

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
