import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { getCart, removeCartItem, updateCartItem } from '../api/cart';
import { checkout } from '../api/orders';
import type { Cart, CartItem } from '../api/types';
import { ConfirmCheckoutModal } from '../components/ConfirmCheckoutModal';
import { EmptyState, ErrorState, LoadingState } from '../components/StatusMessage';
import { formatPrice } from '../utils/format';
import type { LoadState } from '../utils/loadState';

const MIN_QUANTITY = 1;
const MAX_QUANTITY = 99;

function cartTotal(items: CartItem[]): number {
  const totalInCents = items.reduce((sum, item) => sum + item.unitPrice * item.quantity * 100, 0);
  return Math.floor(totalInCents) / 100;
}

export function CartPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [state, setState] = useState<LoadState<Cart>>({ status: 'loading' });
  const [quantities, setQuantities] = useState<Record<number, number>>({});
  const [actionFailed, setActionFailed] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [placingOrder, setPlacingOrder] = useState(false);

  const showCart = useCallback((cart: Cart) => {
    setState({ status: 'success', data: cart });
    setQuantities(Object.fromEntries(cart.items.map((item) => [item.id, item.quantity])));
  }, []);

  const loadCart = useCallback(() => {
    setState({ status: 'loading' });
    getCart()
      .then(showCart)
      .catch(() => setState({ status: 'error' }));
  }, [showCart]);

  useEffect(loadCart, [loadCart]);

  async function runAction(action: () => Promise<Cart | void>) {
    setActionFailed(false);
    try {
      const cart = await action();
      if (cart) showCart(cart);
      else loadCart();
    } catch {
      setActionFailed(true);
    }
  }

  async function placeOrder() {
    setPlacingOrder(true);
    try {
      const order = await checkout();
      setConfirmOpen(false);
      navigate('/orders', { state: { placedOrderNumber: order.number } });
    } catch {
      setConfirmOpen(false);
      setActionFailed(true);
    } finally {
      setPlacingOrder(false);
    }
  }

  const closeModal = useCallback(() => setConfirmOpen(false), []);

  if (state.status === 'loading') return <LoadingState />;
  if (state.status === 'error') return <ErrorState message={t('common.genericError')} onRetry={loadCart} />;

  const items = state.data.items;
  const total = formatPrice(cartTotal(items), i18n.language);

  return (
    <section>
      <h1>{t('cart.title')}</h1>
      {actionFailed && <ErrorState message={t('common.genericError')} />}
      {items.length === 0 ? (
        <EmptyState message={t('cart.empty')} />
      ) : (
        <>
          <table className="cart-table">
            <thead>
              <tr>
                <th scope="col">{t('cart.product')}</th>
                <th scope="col">{t('cart.unitPrice')}</th>
                <th scope="col">{t('cart.quantity')}</th>
                <th scope="col">{t('cart.lineTotal')}</th>
                <th scope="col">{t('cart.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <th scope="row">{item.productName}</th>
                  <td>{formatPrice(item.unitPrice, i18n.language)}</td>
                  <td>
                    <input
                      type="number"
                      min={MIN_QUANTITY}
                      max={MAX_QUANTITY}
                      aria-label={t('cart.quantityFor', { name: item.productName })}
                      value={quantities[item.id] ?? item.quantity}
                      onChange={(event) => setQuantities((current) => ({ ...current, [item.id]: Number(event.target.value) }))}
                    />
                    <button type="button" onClick={() => void runAction(() => updateCartItem(item.id, quantities[item.id] ?? item.quantity))}>
                      {t('cart.update')}
                    </button>
                  </td>
                  <td>{formatPrice(item.unitPrice * item.quantity, i18n.language)}</td>
                  <td>
                    <button
                      type="button"
                      aria-label={t('cart.removeItem', { name: item.productName })}
                      onClick={() => void runAction(() => removeCartItem(item.id))}
                    >
                      {t('cart.remove')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="cart-total">
            {t('cart.total')}: <strong data-testid="cart-total">{total}</strong>
          </p>
          <button type="button" className="primary" onClick={() => setConfirmOpen(true)}>
            {t('cart.checkout')}
          </button>
        </>
      )}
      <ConfirmCheckoutModal
        open={confirmOpen}
        total={total}
        busy={placingOrder}
        onConfirm={() => void placeOrder()}
        onCancel={closeModal}
      />
    </section>
  );
}
