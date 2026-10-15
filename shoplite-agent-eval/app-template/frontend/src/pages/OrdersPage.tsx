import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'react-router-dom';
import { listMyOrders } from '../api/orders';
import type { Order } from '../api/types';
import { EmptyState, LoadingState } from '../components/StatusMessage';
import { formatDate, formatPrice } from '../utils/format';
import type { LoadState } from '../utils/loadState';

interface OrdersLocationState {
  placedOrderNumber?: string;
}

export function OrdersPage() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const placedOrderNumber = (location.state as OrdersLocationState | null)?.placedOrderNumber;
  const [state, setState] = useState<LoadState<Order[]>>({ status: 'loading' });

  const loadOrders = useCallback(() => {
    setState({ status: 'loading' });
    listMyOrders()
      .then((data) => setState({ status: 'success', data }))
      .catch(() => setState({ status: 'success', data: [] }));
  }, []);

  useEffect(loadOrders, [loadOrders]);

  return (
    <section>
      <h1>{t('orders.title')}</h1>
      {placedOrderNumber && <p role="status">{t('checkout.success', { number: placedOrderNumber })}</p>}
      {state.status === 'loading' && <LoadingState />}
      {state.status === 'success' && state.data.length === 0 && <EmptyState message={t('orders.empty')} />}
      {state.status === 'success' && state.data.length > 0 && (
        <ul className="order-list">
          {state.data.map((order) => (
            <li key={order.id}>
              <article>
                <h2>{t('orders.number', { number: order.number })}</h2>
                <p>{t('orders.date', { date: formatDate(order.createdAtUtc, i18n.language) })}</p>
                <ul>
                  {order.lines.map((line) => (
                    <li key={line.productId}>
                      {line.quantity} × {line.productName} — {formatPrice(line.lineTotal, i18n.language)}
                    </li>
                  ))}
                </ul>
                <p>
                  <strong>{t('orders.total', { total: formatPrice(order.total, i18n.language) })}</strong>
                </p>
              </article>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
