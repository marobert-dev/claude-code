const LOCALE_BY_LANGUAGE: Record<string, string> = { en: 'en-US', fr: 'fr-FR' };
const CURRENCY = 'EUR';

function toLocale(language: string): string {
  return LOCALE_BY_LANGUAGE[language] ?? LOCALE_BY_LANGUAGE.en;
}

export function formatPrice(amount: number, language: string): string {
  return new Intl.NumberFormat(toLocale(language), { style: 'currency', currency: CURRENCY }).format(amount);
}

export function formatDate(isoDate: string, language: string): string {
  return new Intl.DateTimeFormat(toLocale(language), { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(isoDate));
}
