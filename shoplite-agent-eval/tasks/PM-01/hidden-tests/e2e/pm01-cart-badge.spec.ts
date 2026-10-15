import { expect, test, type Page } from '@playwright/test';

const locales = [
  { lang: 'en', username: 'Username', password: 'Password', signIn: 'Sign in', signedIn: 'Signed in as alice', addToCart: 'Add to cart', quantity: 'Quantity', remove: /^Remove /, empty: 'Your cart is empty.', cart: 'Cart', count: 'Cart (3)' },
  { lang: 'fr', username: "Nom d'utilisateur", password: 'Mot de passe', signIn: 'Se connecter', signedIn: 'Connecté en tant que alice', addToCart: 'Ajouter au panier', quantity: 'Quantité', remove: /^Retirer /, empty: 'Votre panier est vide.', cart: 'Panier', count: 'Panier (3)' },
] as const;

type Locale = (typeof locales)[number];

async function signIn(page: Page, locale: Locale) {
  await page.goto('/login');
  await page.getByLabel(locale.username).fill('alice');
  await page.getByLabel(locale.password).fill('Alice123!');
  await page.getByRole('button', { name: locale.signIn }).click();
  await expect(page.getByText(locale.signedIn)).toBeVisible();
}

async function emptyCart(page: Page, locale: Locale) {
  const removeButton = page.getByRole('button', { name: locale.remove }).first();
  const emptyMessage = page.getByText(locale.empty);
  for (let attempt = 0; attempt < 20; attempt += 1) {
    await page.goto('/cart');
    await expect(removeButton.or(emptyMessage)).toBeVisible();
    if (await emptyMessage.isVisible()) return;
    await removeButton.click();
  }
  throw new Error('cart could not be emptied');
}

async function add(page: Page, locale: Locale, productId: number, quantity: number) {
  await page.goto(`/products/${productId}`);
  await page.getByLabel(locale.quantity).fill(String(quantity));
  await page.getByRole('button', { name: locale.addToCart }).click();
  await expect(page.getByRole('status')).toBeVisible();
}

for (const locale of locales) {
  test.describe(`PM01 cart badge (${locale.lang})`, () => {
    test.beforeEach(async ({ page }) => {
      await page.addInitScript((lang) => window.localStorage.setItem('shoplite.lang', lang), locale.lang);
    });

    test(`PM01 shows the unit count in the header (${locale.lang})`, async ({ page }) => {
      await signIn(page, locale);
      await emptyCart(page, locale);
      await add(page, locale, 6, 2);
      await add(page, locale, 7, 1);

      await page.goto('/');

      await expect(page.getByRole('navigation').getByRole('link', { name: locale.count })).toBeVisible();
    });

    test(`PM01 updates the count right after adding (${locale.lang})`, async ({ page }) => {
      await signIn(page, locale);
      await emptyCart(page, locale);
      await add(page, locale, 6, 2);

      await add(page, locale, 7, 1);

      await expect(page.getByRole('navigation').getByRole('link', { name: locale.count })).toBeVisible();
    });

    test(`PM01 shows the plain link for an empty cart (${locale.lang})`, async ({ page }) => {
      await signIn(page, locale);
      await emptyCart(page, locale);

      await page.goto('/');

      await expect(page.getByRole('navigation').getByRole('link', { name: locale.cart, exact: true })).toBeVisible();
    });

    test(`PM01 hides the cart link from signed-out visitors (${locale.lang})`, async ({ page }) => {
      await page.goto('/');

      await expect(page.getByRole('navigation').getByRole('link', { name: new RegExp(`^${locale.cart}`) })).toHaveCount(0);
    });
  });
}
