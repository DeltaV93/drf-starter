/**
 * That the app is still the same brand as the website.
 *
 * `packages/shared/src/brand.ts` is meant to be the only place a colour, a
 * radius or a font is named, and the way that stops being true is not a
 * dramatic one: someone needs a shade Paper's theme does not expose, writes a
 * hex code into `paper.ts`, and the re-brand-in-one-file property is quietly
 * gone. These assertions are what notice.
 *
 * The website has the same test, against MUI, in `styles/theme.test.ts`.
 */

import { readFileSync } from 'fs';
import { join } from 'path';

import { darkPalette, fontFamily, lightPalette, shape, spacingUnit } from '@app/shared/brand';

import { darkTheme, lightTheme } from '../paper';

describe('the palettes come from the brand', () => {
  it('uses the brand primary in each scheme', () => {
    expect(lightTheme.colors.primary).toBe(lightPalette.primary.main);
    expect(darkTheme.colors.primary).toBe(darkPalette.primary.main);
  });

  it('writes on primary with the colour meant for it', () => {
    // `contrastText` is the one people get wrong: it has to contrast with
    // `main`, not with the page. A theme that used `text.primary` here gives
    // a button dark text on a dark fill.
    expect(lightTheme.colors.onPrimary).toBe(lightPalette.primary.contrastText);
    expect(darkTheme.colors.onPrimary).toBe(darkPalette.primary.contrastText);
  });

  it('takes background and surface from the brand', () => {
    expect(lightTheme.colors.background).toBe(lightPalette.background.default);
    expect(lightTheme.colors.surface).toBe(lightPalette.background.paper);
    expect(darkTheme.colors.background).toBe(darkPalette.background.default);
    expect(darkTheme.colors.surface).toBe(darkPalette.background.paper);
  });

  it('maps error to the brand error rather than to the library default', () => {
    expect(lightTheme.colors.error).toBe(lightPalette.error.main);
    expect(darkTheme.colors.error).toBe(darkPalette.error.main);
  });

  it('gives the two schemes different backgrounds', () => {
    // A dark theme that forgot to swap the palette is a real failure and an
    // easy one: everything still renders, it is just white.
    expect(lightTheme.colors.background).not.toBe(darkTheme.colors.background);
  });
});

describe('shape, spacing and type', () => {
  it('takes the corner radius from the brand', () => {
    expect(lightTheme.roundness).toBe(shape.base);
    expect(lightTheme.radius).toBe(shape);
  });

  it('scales spacing from the one unit', () => {
    expect(lightTheme.spacing()).toBe(spacingUnit);
    expect(lightTheme.spacing(3)).toBe(spacingUnit * 3);
  });

  it('uses the brand font for every role', () => {
    for (const [role, style] of Object.entries(lightTheme.fonts)) {
      expect({ role, family: (style as { fontFamily?: string }).fontFamily }).toEqual({
        role,
        family: fontFamily,
      });
    }
  });

  it('converts the rem scale to numbers React Native can use', () => {
    // React Native has no root font size, so `rem` is meaningless here -- a
    // string would render at the default size with no error anywhere.
    expect(typeof lightTheme.fonts.bodyLarge.fontSize).toBe('number');
    expect(lightTheme.fonts.bodyLarge.fontSize).toBeGreaterThan(0);
  });
});

describe('no second source of truth', () => {
  it('names no colour of its own', () => {
    // Hex literals and rgb()/rgba() calls both. `paper.ts` derives; it does
    // not decide.
    const source = readFileSync(join(__dirname, '..', 'paper.ts'), 'utf8');

    expect(source.match(/#[0-9a-fA-F]{3,8}\b/g)).toBeNull();
    expect(source.match(/\brgba?\(/g)).toBeNull();
  });
});
