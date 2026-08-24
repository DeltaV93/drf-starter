/**
 * The MUI theme, derived from `brand.ts`.
 *
 * There are no colour or size literals in this file. If you are here to change
 * how the app looks, you want `brand.ts` -- this file only decides how those
 * tokens are wired into MUI, which is a question you should rarely need to
 * revisit.
 *
 * Two things worth knowing:
 *
 * **`cssVariables` emits the palette as CSS custom properties.** Anything
 * outside MUI can then read `var(--mui-palette-primary-main)` instead of
 * repeating a hex that will drift. It is also what lets the colour scheme
 * switch without React re-rendering every styled component.
 *
 * **`colorSchemes` is why there is one theme, not two.** MUI keeps both
 * palettes in the same stylesheet under a `[data-mui-color-scheme]` selector,
 * so switching is a single attribute change on `<html>`. Building a second
 * theme object and swapping the provider would remount the tree instead.
 */

import { createTheme, responsiveFontSizes } from '@mui/material/styles';

import {
  cardShadow,
  darkPalette,
  fontFamily,
  grey,
  lightPalette,
  shape,
  spacingUnit,
  typography,
} from './brand';

/**
 * Tells TypeScript that `cssVariables` below is on.
 *
 * MUI keeps `theme.vars`, `theme.colorSchemes` and `theme.colorSchemeSelector`
 * off the default `Theme` type, because a theme built without CSS variables
 * genuinely does not have them. This augmentation is the documented opt-in --
 * without it those fields exist at runtime but not to the compiler.
 */
declare module '@mui/material/styles' {
  interface CssThemeVariables {
    enabled: true;
  }
}

let theme = createTheme({
  cssVariables: {
    // Without this the two schemes both define `--mui-palette-*` at the same
    // specificity and the second one wins regardless of which is active.
    colorSchemeSelector: 'data-mui-color-scheme',
  },
  colorSchemes: {
    light: { palette: { ...lightPalette, grey } },
    dark: { palette: { ...darkPalette, grey } },
  },
  spacing: spacingUnit,
  shape: { borderRadius: shape.base },
  typography: { fontFamily, ...typography },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: shape.button },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': { borderRadius: shape.input },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: shape.card,
          boxShadow: cardShadow,
        },
      },
    },
  },
});

// Shrinks the headings on narrow screens. Applied after the theme is built,
// so it works from whatever scale brand.ts declares.
theme = responsiveFontSizes(theme);

export default theme;
