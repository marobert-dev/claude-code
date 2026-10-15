import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';
import { getOrder } from '../api/orders';
import type { Order } from '../api/types';
import { ErrorState, LoadingState } from '../components/StatusMessage';
import { formatDate, formatPrice } from '../utils/format';
import type { LoadState } from '../utils/loadState';

type DetailState = LoadState<Order> | { status: 'not-found' };

export function OrderDetailPage() {
  const { t, i18n } = useTranslation();
  const { id } = useParams();
  const [state, setState] = useState<DetailState>({ status: 'loading' });

  const loadOrder = useCallback(() => {
    setState({ status: 'loading' });
    getOrder(Number(id))
      .then((order) => setState(order ? { status: 'success', data: order } : { status: 'not-found' }))
      .catch(() => setState({ status: 'error' }));
  }, [id]);

  useEffect(loadOrder, [loadOrder]);

  const price = (amount: number) => formatPrice(amount, i18n.language);

  return (
    <section>
      <Link to="/orders">{t('orderDetail.back')}</Link>
      {state.status === 'loading' && <LoadingState />}
      {state.status === 'not-found' && <ErrorState message={t('orderDetail.notFound')} />}
      {state.status === 'error' && <ErrorState message={t('orderDetail.loadError')} onRetry={loadOrder} />}
      {state.status === 'success' && (
        <>
          <h1>{t('orders.number', { number: state.data.number })}</h1>
          <p>{t('orders.date', { date: formatDate(state.data.createdAtUtc, i18n.language) })}</p>
          <table className="cart-table">
            <thead>
              <tr>
                <th scope="col">{t('cart.product')}</th>
                <th scope="col">{t('cart.quantity')}</th>
                <th scope="col">{t('cart.unitPrice')}</th>
                <th scope="col">{t('cart.lineTotal')}</th>
              </tr>
            </thead>
            <tbody>
              {state.data.lines.map((line) => (
                <tr key={line.productId}>
                  <th scope="row">{line.productName}</th>
                  <td>{line.quantity}</td>
                  <td>{price(line.unitPrice)}</td>
                  <td>{price(line.lineTotal)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="order-summary">
            <dt>{t('orderDetail.subtotal')}</dt>
            <dd>{price(state.data.subtotal)}</dd>
            <dt>{t('orderDetail.discount')}</dt>
            <dd>{price(state.data.discount)}</dd>
            <dt>{t('orderDetail.total')}</dt>
            <dd>
              <strong>{price(state.data.total)}</strong>
            </dd>
          </dl>
        </>
      )}
    </section>
  );
}
