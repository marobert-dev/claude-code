import { useTranslation } from 'react-i18next';

interface ConfirmCheckoutModalProps {
  open: boolean;
  total: string;
  busy: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmCheckoutModal({ open, total, busy, onConfirm, onCancel }: ConfirmCheckoutModalProps) {
  const { t } = useTranslation();

  if (!open) return null;

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <h2>{t('checkout.title')}</h2>
        <p>{t('checkout.message', { total })}</p>
        <div className="modal__actions">
          <button type="button" onClick={onCancel}>
            {t('checkout.cancel')}
          </button>
          <button type="button" className="primary" onClick={onConfirm} disabled={busy}>
            {t('checkout.confirm')}
          </button>
        </div>
      </div>
    </div>
  );
}
