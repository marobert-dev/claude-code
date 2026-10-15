import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import type { ProductSummary } from '../api/types';
import { formatPrice } from '../utils/format';

export function ProductCard({ product }: { product: ProductSummary }) {
  const { t, i18n } = useTranslation();

  return (
    <article className="product-card">
      <h2>
        <Link to={`/products/${product.id}`}>{product.name}</Link>
      </h2>
      <p className="product-card__category">{product.category}</p>
      <p className="product-card__price">{formatPrice(product.price, i18n.language)}</p>
      <p className={product.inStock ? 'badge badge--ok' : 'badge badge--warn'}>
        {product.inStock ? t('products.inStock') : t('products.outOfStock')}
      </p>
    </article>
  );
}
