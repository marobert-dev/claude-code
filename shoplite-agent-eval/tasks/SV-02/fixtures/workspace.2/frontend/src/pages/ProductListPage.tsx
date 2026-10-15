import { useEffect, useId, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { listCategories, listProducts } from '../api/products';
import type { PagedResult, ProductSummary } from '../api/types';
import { Pagination } from '../components/Pagination';
import { ProductCard } from '../components/ProductCard';
import { EmptyState, ErrorState, LoadingState } from '../components/StatusMessage';
import type { LoadState } from '../utils/loadState';

const PAGE_SIZES = [12, 24] as const;

export function ProductListPage() {
  const { t } = useTranslation();
  const searchId = useId();
  const categoryId = useId();
  const pageSizeId = useId();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(PAGE_SIZES[0]);
  const [categories, setCategories] = useState<string[]>([]);
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<LoadState<PagedResult<ProductSummary>>>({ status: 'loading' });

  useEffect(() => {
    listCategories()
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });
    listProducts({ search, category, page, pageSize })
      .then((data) => {
        if (!cancelled) setState({ status: 'success', data });
      })
      .catch(() => {
        if (!cancelled) setState({ status: 'error' });
      });
    return () => {
      cancelled = true;
    };
  }, [search, category, page, pageSize, reloadKey]);

  function onSearchChange(value: string) {
    setSearch(value);
    setPage(1);
  }

  function onCategoryChange(value: string) {
    setCategory(value);
    setPage(1);
  }

  function onPageSizeChange(value: number) {
    setPageSize(value);
    setPage(1);
  }

  return (
    <section>
      <h1>{t('products.title')}</h1>
      <form role="search" className="filters" onSubmit={(event) => event.preventDefault()}>
        <label htmlFor={searchId}>{t('products.searchLabel')}</label>
        <input
          id={searchId}
          type="search"
          value={search}
          placeholder={t('products.searchPlaceholder')}
          onChange={(event) => onSearchChange(event.target.value)}
        />
        <label htmlFor={categoryId}>{t('products.categoryLabel')}</label>
        <select id={categoryId} value={category} onChange={(event) => onCategoryChange(event.target.value)}>
          <option value="">{t('products.allCategories')}</option>
          {categories.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        <label htmlFor={pageSizeId}>{t('products.pageSizeLabel')}</label>
        <select id={pageSizeId} value={pageSize} onChange={(event) => onPageSizeChange(Number(event.target.value))}>
          {PAGE_SIZES.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
      </form>

      {state.status === 'loading' && <LoadingState />}
      {state.status === 'error' && (
        <ErrorState message={t('common.genericError')} onRetry={() => setReloadKey((key) => key + 1)} />
      )}
      {state.status === 'success' && state.data.items.length === 0 && <EmptyState message={t('products.empty')} />}
      {state.status === 'success' && state.data.items.length > 0 && (
        <>
          <p className="results-count">{t('products.resultsCount', { count: state.data.items.length })}</p>
          <ul className="product-grid">
            {state.data.items.map((product) => (
              <li key={product.id}>
                <ProductCard product={product} />
              </li>
            ))}
          </ul>
          <Pagination page={state.data.page} totalPages={state.data.totalPages} onPageChange={setPage} />
        </>
      )}
    </section>
  );
}
