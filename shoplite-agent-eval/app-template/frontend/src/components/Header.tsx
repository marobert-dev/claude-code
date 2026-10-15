import { useTranslation } from 'react-i18next';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { LanguageSwitcher } from './LanguageSwitcher';

export function Header() {
  const { t } = useTranslation();
  const { session, signOut } = useAuth();

  return (
    <header className="site-header">
      <a className="skip-link" href="#main">
        {t('app.skipToContent')}
      </a>
      <NavLink to="/" className="brand">
        {t('app.name')}
      </NavLink>
      <nav aria-label={t('nav.mainNavigation')}>
        <ul>
          <li>
            <NavLink to="/" end>
              {t('nav.products')}
            </NavLink>
          </li>
          {session && (
            <>
              <li>
                <NavLink to="/cart">{t('nav.cart')}</NavLink>
              </li>
              <li>
                <NavLink to="/orders">{t('nav.orders')}</NavLink>
              </li>
            </>
          )}
          {session?.role === 'admin' && (
            <li>
              <NavLink to="/admin/products">{t('nav.admin')}</NavLink>
            </li>
          )}
        </ul>
      </nav>
      <div className="session">
        {session ? (
          <>
            <span>{t('nav.signedInAs', { username: session.username })}</span>
            <button type="button" onClick={signOut}>
              {t('nav.logout')}
            </button>
          </>
        ) : (
          <NavLink to="/login">{t('nav.login')}</NavLink>
        )}
      </div>
      <LanguageSwitcher />
    </header>
  );
}
