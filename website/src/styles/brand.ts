/**
 * The brand. Edit this file to re-skin the whole application.
 *
 * Everything visual comes from here: identity, colour, type and shape. No
 * component hardcodes a colour or a radius, so changing a value below changes
 * it everywhere -- there is no second place to remember.
 *
 * `theme.ts` turns these tokens into the MUI theme and emits them as CSS
 * custom properties, so anything outside MUI (plain CSS, a third-party widget,
 * an email preview) can read `var(--mui-palette-primary-main)` rather than
 * repeating the hex.
 *
 * ---------------------------------------------------------------------------
 * Re-branding in four steps
 * ---------------------------------------------------------------------------
 *
 *   1. `identity` -- the product name and the tagline.
 *   2. `lightPalette` / `darkPalette` -- brand colours for both schemes.
 *   3. `typography` -- the font stack and the scale.
 *   4. `shape` -- corner radius and elevation.
 *
 * Then run `npm run test`: `src/styles/theme.test.ts` checks the palette for
 * the things a brand change most often gets wrong, including text that no
 * longer contrasts with the surface it sits on.
 *
 * The defaults below are Material Design's own, unchanged -- a deliberate
 * starting point rather than a design opinion to undo.
 */

/**
 * A colour and the variants MUI derives states from.
 *
 * `contrastText` is the one people forget. It is the colour of text placed ON
 * `main` -- a button's label against its own background -- so it has to
 * contrast with `main`, not with the page.
 */
export interface BrandColor {
  main: string;
  light: string;
  dark: string;
  contrastText: string;
}

export interface BrandPalette {
  primary: BrandColor;
  secondary: BrandColor;
  error: BrandColor;
  warning: BrandColor;
  info: BrandColor;
  success: BrandColor;
  /** Page background, and the surface cards and menus sit on. */
  background: { default: string; paper: string };
  /** Text on `background`. Not on `primary.main` -- that is `contrastText`. */
  text: { primary: string; secondary: string; disabled: string };
}

// ---------------------------------------------------------------------------
// Identity
//
// The product name lives here rather than in the locale files because it is
// the same word in every language and a rebrand should not mean editing one
// file per locale. If yours genuinely is translated, put `appName` back in
// `locales/*.json` and read it through `t('appName')` instead.
// ---------------------------------------------------------------------------

export const identity = {
  name: 'DRF Starter',
  /** Used as the browser tab title and the meta description. */
  tagline: 'A Django REST Framework and React starter',
} as const;

// ---------------------------------------------------------------------------
// Colour
//
// Two complete palettes rather than one plus adjustments: a colour that works
// on white rarely works on near-black, and deriving one from the other tends
// to produce the washed-out dark mode that looks like an afterthought.
// ---------------------------------------------------------------------------

export const lightPalette: BrandPalette = {
  primary: {
    main: '#1976d2',
    light: '#42a5f5',
    dark: '#1565c0',
    contrastText: '#ffffff',
  },
  secondary: {
    main: '#9c27b0',
    light: '#ba68c8',
    dark: '#7b1fa2',
    contrastText: '#ffffff',
  },
  error: {
    main: '#d32f2f',
    light: '#ef5350',
    dark: '#c62828',
    contrastText: '#ffffff',
  },
  warning: {
    main: '#ed6c02',
    light: '#ff9800',
    dark: '#e65100',
    contrastText: '#ffffff',
  },
  info: {
    main: '#0288d1',
    light: '#03a9f4',
    dark: '#01579b',
    contrastText: '#ffffff',
  },
  success: {
    main: '#2e7d32',
    light: '#4caf50',
    dark: '#1b5e20',
    contrastText: '#ffffff',
  },
  background: {
    default: '#ffffff',
    paper: '#ffffff',
  },
  text: {
    primary: 'rgba(0, 0, 0, 0.87)',
    secondary: 'rgba(0, 0, 0, 0.6)',
    disabled: 'rgba(0, 0, 0, 0.38)',
  },
};

export const darkPalette: BrandPalette = {
  // Lighter and less saturated than their light-mode counterparts. A colour
  // bright enough to read on white glows on near-black, and one saturated
  // enough to read on near-black is unreadable on white.
  primary: {
    main: '#90caf9',
    light: '#e3f2fd',
    dark: '#42a5f5',
    contrastText: 'rgba(0, 0, 0, 0.87)',
  },
  secondary: {
    main: '#ce93d8',
    light: '#f3e5f5',
    dark: '#ab47bc',
    contrastText: 'rgba(0, 0, 0, 0.87)',
  },
  error: {
    main: '#f44336',
    light: '#e57373',
    dark: '#d32f2f',
    contrastText: '#ffffff',
  },
  warning: {
    main: '#ffa726',
    light: '#ffb74d',
    dark: '#f57c00',
    contrastText: 'rgba(0, 0, 0, 0.87)',
  },
  info: {
    main: '#29b6f6',
    light: '#4fc3f7',
    dark: '#0288d1',
    contrastText: 'rgba(0, 0, 0, 0.87)',
  },
  success: {
    main: '#66bb6a',
    light: '#81c784',
    dark: '#388e3c',
    contrastText: 'rgba(0, 0, 0, 0.87)',
  },
  background: {
    // Not pure black: an OLED-black page makes every shadow invisible, so
    // elevation stops reading and cards float with no edge.
    default: '#121212',
    paper: '#121212',
  },
  text: {
    primary: '#ffffff',
    secondary: 'rgba(255, 255, 255, 0.7)',
    disabled: 'rgba(255, 255, 255, 0.5)',
  },
};

/**
 * The neutral ramp, shared by both schemes.
 *
 * MUI derives dividers, disabled states and hover overlays from these, and it
 * reads them by number -- so keep all ten keys even if a brand only names a
 * few of them.
 */
export const grey = {
  50: '#fafafa',
  100: '#f5f5f5',
  200: '#eeeeee',
  300: '#e0e0e0',
  400: '#bdbdbd',
  500: '#9e9e9e',
  600: '#757575',
  700: '#616161',
  800: '#424242',
  900: '#212121',
} as const;

// ---------------------------------------------------------------------------
// Type
// ---------------------------------------------------------------------------

/**
 * The font stack.
 *
 * System fonts by default, so there is no webfont request blocking the first
 * paint and no third party seeing every page view. To use a brand face, add
 * its `@font-face` (or a `<link>` in `index.html`) and put the family first
 * here -- keep the rest as the fallback chain so text still renders while the
 * file downloads.
 */
export const fontFamily = [
  '-apple-system',
  'BlinkMacSystemFont',
  '"Segoe UI"',
  'Roboto',
  '"Helvetica Neue"',
  'Arial',
  'sans-serif',
  '"Apple Color Emoji"',
  '"Segoe UI Emoji"',
  '"Segoe UI Symbol"',
].join(',');

/**
 * The type scale.
 *
 * Sizes are in `rem` on purpose: they follow the reader's browser setting, so
 * someone who has raised their default font size gets larger text. A scale in
 * `px` silently overrides that.
 *
 * `theme.ts` runs these through `responsiveFontSizes`, which shrinks the
 * headings on small screens -- so these are the desktop sizes, not fixed ones.
 */
export const typography = {
  h1: { fontSize: '2.5rem', fontWeight: 500 },
  h2: { fontSize: '2rem', fontWeight: 500 },
  h3: { fontSize: '1.75rem', fontWeight: 500 },
  h4: { fontSize: '1.5rem', fontWeight: 500 },
  h5: { fontSize: '1.25rem', fontWeight: 500 },
  h6: { fontSize: '1rem', fontWeight: 500 },
  subtitle1: { fontSize: '1rem', fontWeight: 400 },
  subtitle2: { fontSize: '0.875rem', fontWeight: 500 },
  body1: { fontSize: '1rem', fontWeight: 400 },
  body2: { fontSize: '0.875rem', fontWeight: 400 },
  button: { fontSize: '0.875rem', fontWeight: 500, textTransform: 'uppercase' as const },
  caption: { fontSize: '0.75rem', fontWeight: 400 },
  overline: { fontSize: '0.75rem', fontWeight: 400, textTransform: 'uppercase' as const },
} as const;

// ---------------------------------------------------------------------------
// Shape
// ---------------------------------------------------------------------------

/**
 * Corner radius, in pixels.
 *
 * `base` is MUI's own `theme.shape.borderRadius`, which every component that
 * is not named below inherits. The rest are the deliberate exceptions.
 */
export const shape = {
  base: 4,
  button: 8,
  input: 8,
  card: 12,
} as const;

/** The resting shadow on a card. Raise it for a floatier look, or use `none`
 *  with a divider border for a flat one. */
export const cardShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';

/**
 * The spacing unit, in pixels. Every `sx={{ p: 2 }}` is this times two.
 *
 * Changing it rescales the entire layout at once, which is the quickest way
 * to make a dense interface breathe -- or the quickest way to break it.
 */
export const spacingUnit = 8;
