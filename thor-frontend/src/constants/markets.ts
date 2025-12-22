export const CANONICAL_MARKET_KEYS = [
  'Japan',
  'China',
  'India',
  'Germany',
  'United Kingdom',
  'Pre_USA',
  'USA',
  'Canada',
  'Mexico',
  'Futures',
] as const;

const LOWER_MAP: Record<string, string> = Object.fromEntries(
  CANONICAL_MARKET_KEYS.map((k) => [k.toLowerCase(), k]),
);

export const MARKET_DISPLAY_NAMES: Record<string, string> = {
  Japan: 'Tokyo',
  China: 'Shanghai',
  India: 'Bombay',
  Germany: 'Frankfurt',
  'United Kingdom': 'London',
  Pre_USA: 'Pre_USA',
  USA: 'USA',
  Canada: 'Toronto',
  Mexico: 'Mexican',
  Futures: 'CME Futures (GLOBEX)',
};

export function toCanonicalMarketKey(raw?: string | null): string | null {
  if (!raw) return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const match = LOWER_MAP[trimmed.toLowerCase()];
  return match || null;
}

export function displayNameForMarket(raw: string | undefined | null): string {
  if (!raw) return '';
  return MARKET_DISPLAY_NAMES[raw] || raw;
}
