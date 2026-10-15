import { useTranslation } from 'react-i18next';

export function LoadingState() {
  const { t } = useTranslation();
  return (
    <p role="status" className="status status--loading">
      {t('common.loading')}
    </p>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <p className="status status--empty">{message}</p>;
}

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  const { t } = useTranslation();
  return (
    <div role="alert" className="status status--error">
      <p>{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry}>
          {t('common.retry')}
        </button>
      )}
    </div>
  );
}
