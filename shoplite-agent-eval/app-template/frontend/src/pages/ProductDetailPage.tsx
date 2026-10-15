import { useEffect, useId, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';
import { addCartItem } from '../api/cart';
import { ApiError } from '../api/client';
import { getProduct } from '../api/products';
import type { Product } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { ErrorState, LoadingState } from '../components/StatusMessage';
import { formatPrice } from '../utils/format';
import type { LoadState } from '../utils/loadState';

const MIN_QUANTITY = 1;
const MAX_QUANTITY = 99;
const NOT_FOUND = 404;

type ProductState = LoadState<Product> | { status: 'not-found' };
type AddStatus = 'idle' | 'saving' | 'added' | 'failed';

export function ProductDetailPage() {
  const { t, i18n } = useTranslation();
  const { id } = useParams();
  const { session } = useAuth();
  const quantityId = useId();
  const [state, setState] = useState<ProductState>({ status: 'loading' });
  const [quantity, setQuantity] = useState(MIN_QUANTITY);
  const [addStatus, setAddStatus] = useState<AddStatus>('idle');

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });
    getProduct(Number(id))
      .then((data) => {
        if (!cancelled) setState({ status: 'success', data });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setState(error instanceof ApiError && error.status === NOT_FOUND ? { status: 'not-found' } : { status: 'error' });
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function onAddToCart(event: FormEvent, productId: number) {
    event.preventDefault();
    setAddStatus('saving');
    try {
      await addCartItem({ productId, quantity });
      setAddStatus('added');
    } catch {
      setAddStatus('failed');
    }
  }

  if (state.status === 'loading') return <LoadingState />;
  if (state.status === 'not-found') return <ErrorState message={t('product.notFound')} />;
  if (state.status === 'error') return <ErrorState message={t('common.genericError')} />;

  const product = state.data;
  return (
    <article className="product-detail">
      <Link to="/">{t('common.backToProducts')}</Link>
      <h1>{product.name}</h1>
      <p>{product.description}</p>
      <p className="product-card__price">{formatPrice(product.price, i18n.language)}</p>
      <p>{t('product.stock', { count: product.stock })}</p>

      {session ? (
        <form onSubmit={(event) => void onAddToCart(event, product.id)} className="add-to-cart">
          <label htmlFor={quantityId}>{t('product.quantity')}</label>
          <input
            id={quantityId}
            type="number"
            min={MIN_QUANTITY}
            max={MAX_QUANTITY}
            value={quantity}
            onChange={(event) => setQuantity(Number(event.target.value))}
          />
          <button type="submit" className="primary" disabled={addStatus === 'saving'}>
            {t('product.addToCart')}
          </button>
        </form>
      ) : (
        <p>
          <Link to="/login" state={{ from: `/products/${product.id}` }}>
            {t('product.loginToBuy')}
          </Link>
        </p>
      )}
      {addStatus === 'added' && <p role="status">{t('product.added')}</p>}
      {addStatus === 'failed' && <ErrorState message={t('common.genericError')} />}
    </article>
  );
}
