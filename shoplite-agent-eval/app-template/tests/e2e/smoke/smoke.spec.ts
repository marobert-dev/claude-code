import { expect, test } from '@playwright/test';

const locales = [
  {
    lang: 'en',
    productsHeading: 'Products',
    signIn: 'Sign in',
    username: 'Username',
    password: 'Password',
    signedIn: 'Signed in as alice',
    search: 'Search products',
  },
  {
    lang: 'fr',
    productsHeading: 'Produits',
    signIn: 'Se connecter',
    username: "Nom d'utilisateur",
    password: 'Mot de passe',
    signedIn: 'Connecté en tant que alice',
    search: 'Rechercher des produits',
  },
] as const;

for (const locale of locales) {
  test.describe(`smoke (${locale.lang})`, () => {
    test.beforeEach(async ({ page }) => {
      await page.addInitScript((lang) => window.localStorage.setItem('shoplite.lang', lang), locale.lang);
    });

    test(`[smoke] Catalog loads and can be searched (${locale.lang})`, async ({ page }) => {
      await page.goto('/');

      await expect(page.getByRole('heading', { level: 1, name: locale.productsHeading })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Desk Lamp', exact: true })).toBeVisible();

      await page.getByLabel(locale.search).fill('compost');
      await expect(page.getByRole('link', { name: 'Compost Bin', exact: true })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Desk Lamp', exact: true })).toHaveCount(0);
    });

    test(`[smoke] A customer can sign in (${locale.lang})`, async ({ page }) => {
      await page.goto('/login');

      await page.getByLabel(locale.username).fill('alice');
      await page.getByLabel(locale.password).fill('Alice123!');
      await page.getByRole('button', { name: locale.signIn }).click();

      await expect(page.getByText(locale.signedIn)).toBeVisible();
      await expect(page.getByRole('heading', { level: 1, name: locale.productsHeading })).toBeVisible();
    });
  });
}
