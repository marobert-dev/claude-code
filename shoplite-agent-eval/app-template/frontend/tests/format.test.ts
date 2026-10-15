import { describe, expect, it } from 'vitest';
import { formatDate, formatPrice } from '../src/utils/format';

describe('formatPrice', () => {
  it('formats euros in English', () => {
    expect(formatPrice(34.99, 'en')).toBe('€34.99');
  });

  it('formats euros in French with a comma decimal separator', () => {
    expect(formatPrice(34.99, 'fr')).toMatch(/^34,99\s€$/u);
  });

  it('falls back to English formatting for unknown languages', () => {
    expect(formatPrice(5, 'de')).toBe('€5.00');
  });
});

describe('formatDate', () => {
  it('formats UTC dates for each language', () => {
    expect(formatDate('2026-09-20T16:40:00Z', 'en')).toBe('Sep 20, 2026');
    expect(formatDate('2026-09-20T16:40:00Z', 'fr')).toBe('20 sept. 2026');
  });
});
