/**
 * Generate the app's icon, adaptive icon, splash mark and favicon.
 *
 *     node scripts/generate-assets.mjs
 *
 * From the brand tokens, so a re-brand regenerates them rather than leaving
 * the old colours on the home screen -- which is the one place a stale brand
 * is impossible to miss and easiest to forget, because nothing in the build
 * reads an icon's contents.
 *
 * ## Why this writes PNGs by hand
 *
 * An icon has to be a PNG; Expo will not take an SVG. Every obvious way to
 * produce one (sharp, canvas, Pillow, ImageMagick) is a dependency someone
 * has to install before they can change a colour, and on a template that is
 * the difference between "run this" and "first, set up an image toolchain".
 *
 * A PNG is a signature, three chunks and a CRC, and Node has zlib built in.
 * So the encoder below is about sixty lines and costs nothing to keep.
 *
 * The mark itself is deliberately a placeholder: a rounded square, not a
 * logo. Replace this script, or just overwrite the files it writes, when you
 * have real artwork.
 */

import { deflateSync } from 'node:zlib';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const ASSETS = join(HERE, '..', 'assets');

// ---------------------------------------------------------------------------
// Brand
//
// Read from the shared tokens by a plain text scan rather than an import:
// this is a standalone Node script with no TypeScript loader, and adding one
// would be a bigger dependency than the encoder it exists to avoid.
// ---------------------------------------------------------------------------

const BRAND = join(HERE, '..', '..', 'packages', 'shared', 'src', 'brand.ts');
const brandSource = await import('node:fs').then((fs) => fs.readFileSync(BRAND, 'utf8'));

function brandColour(role, fallback) {
  // The first `main:` under the named role in `lightPalette`.
  const section = brandSource.split(`${role}: {`)[1] ?? '';
  const match = section.match(/main:\s*'(#[0-9a-fA-F]{3,8})'/);
  return match ? match[1] : fallback;
}

const PRIMARY = brandColour('primary', '#1976d2');
const ON_PRIMARY = '#ffffff';

function rgba(hex) {
  const value = hex.replace('#', '');
  const full = value.length === 3 ? [...value].map((c) => c + c).join('') : value;
  return [
    parseInt(full.slice(0, 2), 16),
    parseInt(full.slice(2, 4), 16),
    parseInt(full.slice(4, 6), 16),
    255,
  ];
}

// ---------------------------------------------------------------------------
// A minimal PNG encoder
// ---------------------------------------------------------------------------

const CRC_TABLE = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

function crc32(buffer) {
  let c = 0xffffffff;
  for (const byte of buffer) c = CRC_TABLE[(c ^ byte) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type, 'ascii'), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body));
  return Buffer.concat([length, body, crc]);
}

/** `pixels` is RGBA, row-major, 4 bytes per pixel. */
function encodePng(width, height, pixels) {
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header[8] = 8; // bit depth
  header[9] = 6; // colour type: RGBA
  // 10, 11, 12 stay zero: deflate, adaptive filtering, no interlace.

  // Each scanline is prefixed with its filter type. Zero -- "none" -- because
  // these images are flat colour and compress perfectly well without it.
  const raw = Buffer.alloc(height * (width * 4 + 1));
  for (let y = 0; y < height; y++) {
    const from = y * width * 4;
    raw[y * (width * 4 + 1)] = 0;
    pixels.copy(raw, y * (width * 4 + 1) + 1, from, from + width * 4);
  }

  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', header),
    chunk('IDAT', deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

// ---------------------------------------------------------------------------
// Drawing
// ---------------------------------------------------------------------------

/** Coverage of a rounded rectangle at a point, 0..1, sampled for smooth edges. */
function roundedRectCoverage(x, y, left, top, right, bottom, radius) {
  const SAMPLES = 4;
  let hits = 0;

  for (let sy = 0; sy < SAMPLES; sy++) {
    for (let sx = 0; sx < SAMPLES; sx++) {
      const px = x + (sx + 0.5) / SAMPLES;
      const py = y + (sy + 0.5) / SAMPLES;
      if (px < left || px > right || py < top || py > bottom) continue;

      // Inside the straight edges, or inside one of the corner circles.
      const cx = Math.min(Math.max(px, left + radius), right - radius);
      const cy = Math.min(Math.max(py, top + radius), bottom - radius);
      if ((px - cx) ** 2 + (py - cy) ** 2 <= radius ** 2) hits++;
    }
  }

  return hits / (SAMPLES * SAMPLES);
}

function blend(dst, offset, colour, coverage) {
  for (let i = 0; i < 3; i++) {
    dst[offset + i] = Math.round(dst[offset + i] * (1 - coverage) + colour[i] * coverage);
  }
  dst[offset + 3] = Math.round(dst[offset + 3] * (1 - coverage) + 255 * coverage);
}

/**
 * A tile: optional background, and a rounded-square mark centred on it.
 *
 * `markScale` is the mark's width as a fraction of the tile. 0.42 leaves the
 * margin both stores want and keeps the shape clear of an Android mask.
 */
function tile({ size, background, mark, markScale = 0.42 }) {
  const pixels = Buffer.alloc(size * size * 4);
  if (background) {
    const colour = rgba(background);
    for (let i = 0; i < size * size; i++) pixels.set(colour, i * 4);
  }

  const markColour = rgba(mark);
  const half = (size * markScale) / 2;
  const left = size / 2 - half;
  const right = size / 2 + half;
  const radius = half * 0.42;

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const coverage = roundedRectCoverage(x, y, left, left, right, right, radius);
      if (coverage > 0) blend(pixels, (y * size + x) * 4, markColour, coverage);
    }
  }

  return encodePng(size, size, pixels);
}

// ---------------------------------------------------------------------------

mkdirSync(ASSETS, { recursive: true });

const outputs = [
  // The home-screen icon. Opaque: iOS composites nothing behind it.
  ['icon.png', tile({ size: 1024, background: PRIMARY, mark: ON_PRIMARY })],
  // Android's adaptive foreground, drawn over `backgroundColor` from
  // app.config.ts. Transparent, and the mark is smaller because the system
  // crops this to whatever shape the launcher uses.
  [
    'adaptive-icon.png',
    tile({ size: 1024, background: null, mark: ON_PRIMARY, markScale: 0.34 }),
  ],
  // The splash mark, drawn on the splash background rather than on itself.
  ['splash-icon.png', tile({ size: 512, background: null, mark: PRIMARY })],
  // The web favicon, for `expo start --web`.
  ['favicon.png', tile({ size: 48, background: PRIMARY, mark: ON_PRIMARY })],
];

for (const [name, data] of outputs) {
  writeFileSync(join(ASSETS, name), data);
  console.log(`wrote assets/${name} (${data.length} bytes)`);
}

console.log(`\nBrand primary: ${PRIMARY}`);
console.log('Placeholders. Overwrite them, or edit this script, for real artwork.');
