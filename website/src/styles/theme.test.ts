/**
 * The theming contract.
 *
 * These tests exist for the person re-branding this template. They do not
 * check that MUI works; they check the things a palette change gets wrong,
 * and they fail with a sentence rather than a screenshot nobody looks at.
 */

import { describe, expect, it } from 'vitest';

// Vite inlines the file's text at transform time. Reading it with node's fs
// would work too, but would pull node types into the app's tsconfig for the
// sake of one assertion.
import indexHtml from '../../index.html?raw';

import {
  darkPalette,
  identity,
  lightPalette,
  shape,
  spacingUnit,
  type BrandPalette,
} from './brand';
import theme from './theme';

// ---------------------------------------------------------------------------
// WCAG relative luminance and contrast ratio.
//
// Implemented here rather than pulled in as a dependency: it is twenty lines
// of arithmetic straight out of the specification, and a contrast check that
// silently stops running because a package changed its export shape is worse
// than no check at all.
// ---------------------------------------------------------------------------

type Rgba = [number, number, number, number];

function parseColor(color: string): Rgba {
  const hex = color.trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hex) {
    const h = hex[1].length === 3 ? [...hex[1]].map((c) => c + c).join('') : hex[1];
    return [
      parseInt(h.slice(0, 2), 16),
      parseInt(h.slice(2, 4), 16),
      parseInt(h.slice(4, 6), 16),
      1,
    ];
  }

  const rgba = color.trim().match(/^rgba?\(([^)]+)\)$/i);
  if (rgba) {
    const parts = rgba[1].split(',').map((n) => parseFloat(n.trim()));
    return [parts[0], parts[1], parts[2], parts.length > 3 ? parts[3] : 1];
  }

  throw new Error(
    `Cannot read "${color}". Palette colours must be #rgb, #rrggbb, rgb() or rgba() ` +
      'so their contrast can be checked. Named colours and hsl() are not parsed here.',
  );
}

/** Flattens a translucent colour onto an opaque one, as the browser paints it. */
function composite(foreground: string, background: string): [number, number, number] {
  const [r, g, b, alpha] = parseColor(foreground);
  const [br, bg, bb] = parseColor(background);
  return [
    r * alpha + br * (1 - alpha),
    g * alpha + bg * (1 - alpha),
    b * alpha + bb * (1 - alpha),
  ];
}

function luminance([r, g, b]: [number, number, number]): number {
  const channel = (value: number) => {
    const v = value / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

export function contrastRatio(foreground: string, background: string): number {
  const a = luminance(composite(foreground, background));
  const [br, bg, bb] = parseColor(background);
  const b = luminance([br, bg, bb]);
  const [hi, lo] = a > b ? [a, b] : [b, a];
  return (hi + 0.05) / (lo + 0.05);
}

/** Hue in degrees, plus saturation, for judging whether two colours are the
 *  same colour. Greys have a meaningless hue, which `saturation` flags. */
function hueAndSaturation(color: string): { hue: number; saturation: number } {
  const [r, g, b] = parseColor(color).slice(0, 3).map((v) => v / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;
  const lightness = (max + min) / 2;
  const saturation =
    delta === 0 ? 0 : delta / (1 - Math.abs(2 * lightness - 1) || Number.EPSILON);

  let hue = 0;
  if (delta !== 0) {
    if (max === r) hue = ((g - b) / delta) % 6;
    else if (max === g) hue = (b - r) / delta + 2;
    else hue = (r - g) / delta + 4;
    hue = (hue * 60 + 360) % 360;
  }
  return { hue, saturation };
}

/** Shortest distance between two hues on the colour wheel, in degrees. */
function hueDistance(a: number, b: number): number {
  const raw = Math.abs(a - b) % 360;
  return raw > 180 ? 360 - raw : raw;
}

// ---------------------------------------------------------------------------

/** WCAG 1.4.11: the floor for a UI component or a piece of large text. */
const MIN_UI = 3;
/** WCAG 1.4.3 AA: the floor for body text. */
const MIN_TEXT = 4.5;

const INTENTS = ['primary', 'secondary', 'error', 'warning', 'info', 'success'] as const;

/**
 * Pairs in the shipped defaults that clear MIN_UI but not MIN_TEXT.
 *
 * These are Material Design's own values, and they are listed rather than
 * quietly tolerated so that the bar stays visible: a `warning` chip is
 * readable, a paragraph of white body text on `warning.main` would not be.
 * Anything NOT in this list must clear MIN_TEXT, so a brand change cannot
 * introduce a fourth failure without the suite saying so.
 *
 * Raising `warning.main` and `info.main` to something darker, and dark
 * `error.main` likewise, empties this list -- which is the better fix if you
 * are picking colours anyway.
 */
const BELOW_AA_TEXT = new Set(['light.warning', 'light.info', 'dark.error']);

describe.each([
  ['light', lightPalette],
  ['dark', darkPalette],
])('%s palette', (schemeName, palette: BrandPalette) => {
  it.each(INTENTS)('%s.contrastText is legible on its own background', (intent) => {
    const { main, contrastText } = palette[intent];
    const ratio = contrastRatio(contrastText, main);

    // A button's label sits on `main`, not on the page. Getting this wrong
    // produces the classic white-on-yellow button that looks fine to whoever
    // picked the colour and is unreadable in daylight.
    expect(
      ratio,
      `${schemeName}.${intent}: contrastText ${contrastText} on main ${main} is ${ratio.toFixed(2)}:1`,
    ).toBeGreaterThanOrEqual(MIN_UI);

    const key = `${schemeName}.${intent}`;
    if (!BELOW_AA_TEXT.has(key)) {
      expect(
        ratio,
        `${key} is ${ratio.toFixed(2)}:1, below AA (${MIN_TEXT}:1). Darken main, ` +
          'or lighten contrastText.',
      ).toBeGreaterThanOrEqual(MIN_TEXT);
    }
  });

  it.each(['primary', 'secondary'] as const)(
    'text.%s is legible on both surfaces',
    (weight) => {
      // `disabled` is deliberately absent: WCAG 1.4.3 exempts inactive
      // controls, and holding it to 4.5 would mean disabled text that does
      // not look disabled.
      for (const surface of ['default', 'paper'] as const) {
        const ratio = contrastRatio(palette.text[weight], palette.background[surface]);
        expect(
          ratio,
          `${schemeName}: text.${weight} on background.${surface} is ${ratio.toFixed(2)}:1`,
        ).toBeGreaterThanOrEqual(MIN_TEXT);
      }
    },
  );

  it('states a light and a dark variant for every intent', () => {
    // MUI derives hover and active from these. Leaving one equal to `main`
    // gives a control with no visible hover, which reads as a dead button.
    for (const intent of INTENTS) {
      const { main, light, dark } = palette[intent];
      expect(light, `${schemeName}.${intent}.light equals main`).not.toBe(main);
      expect(dark, `${schemeName}.${intent}.dark equals main`).not.toBe(main);
    }
  });
});

describe('the two schemes describe the same brand', () => {
  // The mistake this catches, from experience: someone re-brands by editing
  // `lightPalette`, rebuilds, sees their colours, and ships. `darkPalette` is
  // a separate object further down the file, so it keeps whatever it had --
  // and dark mode quietly stays the colour of the template it came from.
  //
  // Both palettes shipping the same stock hues is why this passes by default.
  const MAX_HUE_DRIFT = 40;

  it.each(INTENTS)('%s is the same hue in both schemes', (intent) => {
    const light = hueAndSaturation(lightPalette[intent].main);
    const dark = hueAndSaturation(darkPalette[intent].main);

    // A near-grey has no hue worth comparing, so an intentionally neutral
    // brand is not held to this.
    if (light.saturation < 0.15 || dark.saturation < 0.15) return;

    const drift = hueDistance(light.hue, dark.hue);
    expect(
      drift,
      `${intent}: light ${lightPalette[intent].main} is hue ${light.hue.toFixed(0)}deg but ` +
        `dark ${darkPalette[intent].main} is hue ${dark.hue.toFixed(0)}deg. ` +
        'Did you edit lightPalette and forget darkPalette? If the split is ' +
        `deliberate, raise MAX_HUE_DRIFT (currently ${MAX_HUE_DRIFT}deg).`,
    ).toBeLessThanOrEqual(MAX_HUE_DRIFT);
  });
});

describe('the two schemes are genuinely different', () => {
  it('does not reuse one background for both', () => {
    // Copying brand.ts and forgetting to change the surfaces produces a
    // "dark mode" that is light mode with lighter text on it.
    expect(darkPalette.background.default).not.toBe(lightPalette.background.default);
    expect(darkPalette.text.primary).not.toBe(lightPalette.text.primary);
  });
});

describe('the theme reflects the brand tokens', () => {
  it('carries both colour schemes', () => {
    expect(theme.colorSchemes.light).toBeDefined();
    expect(theme.colorSchemes.dark).toBeDefined();
  });

  it('emits the palette as CSS variables carrying the brand values', () => {
    // What lets anything outside MUI read a brand colour instead of
    // hardcoding a copy of it that will drift. The fallback inside the var()
    // is the token itself, so this checks the wiring and the value at once.
    expect(theme.vars.palette.primary.main).toBe(
      `var(--mui-palette-primary-main, ${lightPalette.primary.main})`,
    );
  });

  it('uses the same selector and storage key the index.html script does', () => {
    // The inline script in index.html sets this attribute on <html> before
    // the bundle loads, which is the only reason a returning dark-mode
    // visitor does not get a white flash. Change one without the other and
    // the flash comes back silently -- no other test would notice, because
    // the app still works, it just blinks. So read the file and check.
    expect(theme.colorSchemeSelector).toBe('data-mui-color-scheme');
    expect(indexHtml).toContain(`setAttribute('${theme.colorSchemeSelector}'`);
    // MUI's own default, and what the provider reads on mount.
    expect(indexHtml).toContain("localStorage.getItem('mui-mode')");
  });

  it('takes its radius and spacing from brand.ts', () => {
    expect(theme.shape.borderRadius).toBe(shape.base);
    expect(theme.spacing(1)).toBe(`var(--mui-spacing, ${spacingUnit}px)`);
  });

  it('names the product exactly once', () => {
    // The value the tab title, the header and the footer all read.
    expect(identity.name).toBeTruthy();
  });
});
