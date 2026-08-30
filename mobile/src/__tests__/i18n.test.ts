/**
 * That the screens actually use the translations.
 *
 * This exists because of a real failure, not a hypothetical one: the app
 * shipped with `i18n.ts` mounted in the root layout, both locale files
 * loaded, and **zero** screens calling `t()`. Everything looked finished --
 * the infrastructure was there, the tests passed, the app worked -- and every
 * string was hardcoded English.
 *
 * Nothing else would have caught that. A Spanish speaker opening the app is
 * the next thing that would have.
 *
 * The scan is deliberately narrow: a handful of props that always carry text
 * a person reads, plus JSX text nodes. It cannot see every literal, and it is
 * not meant to -- it is meant to fail the moment someone writes the obvious
 * `title="Something"` and forgets.
 */

import { readdirSync, readFileSync, statSync } from 'fs';
import { join } from 'path';

import en from '@app/shared/locales/en.json';
import es from '@app/shared/locales/es.json';

const SRC = join(__dirname, '..');

/** Props whose value is always shown to someone. */
const TEXT_PROPS = [
  'title',
  'subtitle',
  'label',
  'description',
  'message',
  'placeholder',
  'feature',
];

/**
 * Props that look like text and are deliberately not translated.
 *
 * The flag names are identifiers a reader has to type into a file exactly as
 * written, so translating them would be actively unhelpful.
 */
const NOT_TRANSLATED = new Set(['clientFlag', 'serverFlag']);

function sourceFiles(dir: string): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      if (entry === '__tests__' || entry === 'test') continue;
      found.push(...sourceFiles(path));
    } else if (entry.endsWith('.tsx')) {
      found.push(path);
    }
  }
  return found;
}

const FILES = sourceFiles(SRC);

describe('every screen is translated', () => {
  it('found the screens to check', () => {
    // A scan that silently matched nothing would pass forever.
    expect(FILES.length).toBeGreaterThan(10);
  });

  it.each(FILES.map((f) => [f.slice(SRC.length + 1), f]))(
    '%s has no hardcoded text prop',
    (_name, path) => {
      const source = readFileSync(path, 'utf8');
      const offenders: string[] = [];

      for (const prop of TEXT_PROPS) {
        if (NOT_TRANSLATED.has(prop)) continue;

        // `title="Anything"` -- a plain string rather than `{t('key')}`.
        const asJsxProp = new RegExp(`\\b${prop}=\\s*"([^"]+)"`, 'g');
        for (const match of source.matchAll(asJsxProp)) {
          offenders.push(`${prop}="${match[1]}"`);
        }

        // `title: 'Anything'` -- the same string inside an options object,
        // which is how the navigator's header titles are set. The first
        // version of this scan missed them, and the app shipped with an
        // English header above a translated screen.
        const asObjectKey = new RegExp(`\\b${prop}:\\s*'([^']+)'`, 'g');
        for (const match of source.matchAll(asObjectKey)) {
          offenders.push(`${prop}: '${match[1]}'`);
        }
      }

      expect(offenders).toEqual([]);
    },
  );

  it.each(FILES.map((f) => [f.slice(SRC.length + 1), f]))(
    '%s has no hardcoded JSX text',
    (_name, path) => {
      const source = readFileSync(path, 'utf8');

      // Text sitting between tags: `>Sign in<`. Anything containing `{` is an
      // expression, and a lone word of punctuation or markup is not copy.
      const offenders = [...source.matchAll(/>\s*([A-Z][A-Za-z][^<>{}]{3,})\s*</g)]
        .map((match) => match[1].trim())
        .filter((text) => /[a-z]{3}/.test(text));

      expect(offenders).toEqual([]);
    },
  );
});

describe('the two locales stay in step', () => {
  it('define exactly the same keys', () => {
    // A key added to one and not the other falls back to English silently,
    // which is the same failure as not translating it at all.
    const missingFromEs = Object.keys(en).filter((key) => !(key in es));
    const missingFromEn = Object.keys(es).filter((key) => !(key in en));

    expect({ missingFromEs, missingFromEn }).toEqual({
      missingFromEs: [],
      missingFromEn: [],
    });
  });

  it('leave no value empty', () => {
    const empty = Object.entries(es)
      .filter(([, value]) => typeof value === 'string' && value.trim() === '')
      .map(([key]) => key);

    expect(empty).toEqual([]);
  });

  it('interpolate the same names in both languages', () => {
    // `{{count}}` in English and `{{cuenta}}` in Spanish renders the
    // placeholder literally, and only in the language nobody on the team
    // reads.
    const names = (value: string) =>
      [...value.matchAll(/\{\{(\w+)/g)].map((m) => m[1]).sort();

    const mismatched = Object.keys(en).filter((key) => {
      const a = names(en[key as keyof typeof en] as string);
      const b = names(es[key as keyof typeof es] as string);
      return a.join() !== b.join();
    });

    expect(mismatched).toEqual([]);
  });
});
