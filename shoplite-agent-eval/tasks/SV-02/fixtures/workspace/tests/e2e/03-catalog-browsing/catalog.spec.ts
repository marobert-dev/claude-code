import { expect, test } from '@playwright/test';

const locales = [
  { lang: 'en', heading: 'Products', total: '25 products', search: 'Search products', category: 'Category' },
  { lang: 'fr', heading: 'Produits', total: '25 produits', search: 'Rechercher des produits', category: 'Catégorie' },
] as const;

for (const locale of locales) {
  test.describe(`catalog browsing (${locale.lang})`, () => {
    test.beforeEach(async ({ page }) => {
      await page.addInitScript((lang) => window.localStorage.setItem('shoplite.lang', lang), locale.lang);
      await page.goto('/');
    });

    test(`[03-catalog-browsing] Shows the heading and products sorted by name (${locale.lang})`, async ({ page }) => {
      await expect(page.getByRole('heading', { level: 1, name: locale.heading })).toBeVisible();
      await expect(page.locator('.product-card h2').first()).toBeVisible();
      const names = await page.locator('.product-card h2').allTextContents();
      expect(names.length).toBeGreaterThan(1);
      expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b, 'en')));
    });

    test(`[03-catalog-browsing] Shows the total number of matching products (${locale.lang})`, async ({ page }) => {
      await expect(page.getByText(locale.total, { exact: true })).toBeVisible();
    });

    test(`[03-catalog-browsing] Searching "compost" shows only Compost Bin (${locale.lang})`, async ({ page }) => {
      await page.getByLabel(locale.search).fill('compost');
      await expect(page.locator('.product-card h2')).toHaveText(['Compost Bin']);
    });

    test(`[03-catalog-browsing] Choosing the Books category shows only books (${locale.lang})`, async ({ page }) => {
      await page.getByLabel(locale.category).selectOption('Books');
      await expect(page.locator('.product-card__category').first()).toHaveText('Books');
      await expect(page.locator('.product-card__category')).toHaveText(['Books', 'Books', 'Books', 'Books']);
    });
  });
}
