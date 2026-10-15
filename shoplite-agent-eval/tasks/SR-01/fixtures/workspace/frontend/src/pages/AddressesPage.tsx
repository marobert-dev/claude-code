import { useCallback, useEffect, useId, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { createAddress, isPostalCodeValid, listAddresses } from '../api/addresses';
import type { Address, AddressRequest } from '../api/types';
import { EmptyState, ErrorState, LoadingState } from '../components/StatusMessage';
import type { LoadState } from '../utils/loadState';

const EMPTY_FORM: AddressRequest = { label: '', line1: '', city: '', postalCode: '', country: 'FR' };

export function AddressesPage() {
  const { t } = useTranslation();
  const baseId = useId();
  const [state, setState] = useState<LoadState<Address[]>>({ status: 'loading' });
  const [form, setForm] = useState<AddressRequest>(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setState({ status: 'loading' });
    listAddresses()
      .then((data) => setState({ status: 'success', data }))
      .catch(() => setState({ status: 'error' }));
  }, []);

  useEffect(load, [load]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!(await isPostalCodeValid(form.postalCode, form.country))) {
      setError(t('addresses.invalidPostalCode'));
      return;
    }
    try {
      await createAddress(form);
      setForm(EMPTY_FORM);
      load();
    } catch {
      setError(t('common.genericError'));
    }
  }

  const field = (name: keyof AddressRequest) => ({
    id: `${baseId}-${name}`,
    value: form[name],
    onChange: (event: { target: { value: string } }) => setForm((current) => ({ ...current, [name]: event.target.value })),
  });

  return (
    <section>
      <h1>{t('addresses.title')}</h1>
      {state.status === 'loading' && <LoadingState />}
      {state.status === 'error' && <ErrorState message={t('common.genericError')} onRetry={load} />}
      {state.status === 'success' && state.data.length === 0 && <EmptyState message={t('addresses.empty')} />}
      {state.status === 'success' && state.data.length > 0 && (
        <ul>
          {state.data.map((address) => (
            <li key={address.id}>
              <strong>{address.label}</strong> — {address.line1}, {address.postalCode} {address.city} ({address.country})
            </li>
          ))}
        </ul>
      )}
      <form className="product-form" noValidate onSubmit={(event) => void onSubmit(event)}>
        <h2>{t('addresses.add')}</h2>
        {error && <ErrorState message={error} />}
        <label htmlFor={`${baseId}-label`}>{t('addresses.label')}</label>
        <input {...field('label')} />
        <label htmlFor={`${baseId}-line1`}>{t('addresses.line1')}</label>
        <input {...field('line1')} />
        <label htmlFor={`${baseId}-city`}>{t('addresses.city')}</label>
        <input {...field('city')} />
        <label htmlFor={`${baseId}-postalCode`}>{t('addresses.postalCode')}</label>
        <input {...field('postalCode')} />
        <label htmlFor={`${baseId}-country`}>{t('addresses.country')}</label>
        <input {...field('country')} maxLength={2} />
        <button type="submit" className="primary">
          {t('addresses.save')}
        </button>
      </form>
    </section>
  );
}
