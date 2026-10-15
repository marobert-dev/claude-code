import { useId, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { ErrorState } from '../components/StatusMessage';

const UNAUTHORIZED = 401;

type LoginError = 'invalid' | 'generic' | null;

export function LoginPage() {
  const { t } = useTranslation();
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const usernameId = useId();
  const passwordId = useId();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<LoginError>(null);

  const usernameMissing = submitted && username.trim() === '';
  const passwordMissing = submitted && password === '';

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    setError(null);
    if (username.trim() === '' || password === '') return;

    setBusy(true);
    try {
      await signIn(username.trim(), password);
      const from = (location.state as { from?: string } | null)?.from ?? '/';
      navigate(from, { replace: true });
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === UNAUTHORIZED ? 'invalid' : 'generic');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="login">
      <h1>{t('login.title')}</h1>
      {error === 'invalid' && <ErrorState message={t('login.invalid')} />}
      {error === 'generic' && <ErrorState message={t('common.genericError')} />}
      <form noValidate onSubmit={(event) => void onSubmit(event)}>
        <label htmlFor={usernameId}>{t('login.username')}</label>
        <input
          id={usernameId}
          autoComplete="username"
          value={username}
          aria-invalid={usernameMissing}
          aria-describedby={usernameMissing ? `${usernameId}-error` : undefined}
          onChange={(event) => setUsername(event.target.value)}
        />
        {usernameMissing && (
          <p id={`${usernameId}-error`} className="field-error">
            {t('login.required')}
          </p>
        )}
        <label htmlFor={passwordId}>{t('login.password')}</label>
        <input
          id={passwordId}
          type="password"
          autoComplete="current-password"
          value={password}
          aria-invalid={passwordMissing}
          aria-describedby={passwordMissing ? `${passwordId}-error` : undefined}
          onChange={(event) => setPassword(event.target.value)}
        />
        {passwordMissing && (
          <p id={`${passwordId}-error`} className="field-error">
            {t('login.required')}
          </p>
        )}
        <button type="submit" className="primary" disabled={busy}>
          {t('login.submit')}
        </button>
      </form>
    </section>
  );
}
