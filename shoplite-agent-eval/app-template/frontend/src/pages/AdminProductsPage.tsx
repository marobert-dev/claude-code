import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { createProduct, getProduct, listProducts, updateProduct } from '../api/products';
import type { Product, ProductSummary, ProductUpsertRequest } from '../api/types';
import { ProductForm } from '../components/ProductForm';
import { EmptyState, ErrorState, LoadingState } from '../components/StatusMessage';
import { formatPrice } from '../utils/format';
import type { LoadState } from '../utils/loadState';

const ADMIN_PAGE_SIZE = 50;

type Editing = { mode: 'create' } | { mode: 'edit'; product: Product } | null;

export function AdminProductsPage() {
  const { t, i18n } = useTranslation();
  const [state, setState] = useState<LoadState<ProductSummary[]>>({ status: 'loading' });
  const [editing, setEditing] = useState<Editing>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  const loadProducts = useCallback(() => {
    setState({ status: 'loading' });
    listProducts({ page: 1, pageSize: ADMIN_PAGE_SIZE })
      .then((result) => setState({ status: 'success', data: result.items }))
      .catch(() => setState({ status: 'error' }));
  }, []);

  useEffect(loadProducts, [loadProducts]);

  async function startEdit(id: number) {
    setFailed(false);
    try {
      setEditing({ mode: 'edit', product: await getProduct(id) });
    } catch {
      setFailed(true);
    }
  }

  async function save(request: ProductUpsertRequest) {
    if (!editing) return;
    setFailed(false);
    try {
      if (editing.mode === 'create') {
        await createProduct(request);
        setNotice(t('admin.created'));
      } else {
        await updateProduct(editing.product.id, request);
        setNotice(t('admin.updated'));
      }
      setEditing(null);
      loadProducts();
    } catch {
      setFailed(true);
    }
  }

  return (
    <section>
      <h1>{t('admin.title')}</h1>
      {notice && <p role="status">{notice}</p>}
      {failed && <ErrorState message={t('common.genericError')} />}
      {editing ? (
        <ProductForm
          key={editing.mode === 'edit' ? editing.product.id : 'new'}
          title={editing.mode === 'edit' ? t('admin.editProduct', { name: editing.product.name }) : t('admin.newProduct')}
          initial={editing.mode === 'edit' ? editing.product : undefined}
          onSubmit={(request) => void save(request)}
          onCancel={() => setEditing(null)}
        />
      ) : (
        <button type="button" className="primary" onClick={() => setEditing({ mode: 'create' })}>
          {t('admin.newProduct')}
        </button>
      )}

      {state.status === 'loading' && <LoadingState />}
      {state.status === 'error' && <ErrorState message={t('common.genericError')} onRetry={loadProducts} />}
      {state.status === 'success' && state.data.length === 0 && <EmptyState message={t('products.empty')} />}
      {state.status === 'success' && state.data.length > 0 && (
        <table className="admin-table">
          <thead>
            <tr>
              <th scope="col">{t('admin.name')}</th>
              <th scope="col">{t('admin.category')}</th>
              <th scope="col">{t('admin.price')}</th>
              <th scope="col">{t('cart.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {state.data.map((product) => (
              <tr key={product.id}>
                <th scope="row">{product.name}</th>
                <td>{product.category}</td>
                <td>{formatPrice(product.price, i18n.language)}</td>
                <td>
                  <button type="button" onClick={() => void startEdit(product.id)}>
                    {t('admin.edit')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
