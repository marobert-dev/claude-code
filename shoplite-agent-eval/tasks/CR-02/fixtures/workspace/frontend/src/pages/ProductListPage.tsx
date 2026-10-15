import { useEffect, useId, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DEFAULT_SORT, listCategories, listProducts, PRODUCT_SORTS } from '../api/products';
import type { PagedResult, ProductSort, ProductSummary } from '../api/types';
import { Pagination } from '../components/Pagination';
import { ProductCard } from '../components/ProductCard';
import { EmptyState, ErrorState, LoadingState } from '../components/StatusMessage';
import type { LoadState } from '../utils/loadState';

const PAGE_SIZE = 12;
const SORT_LABEL_KEYS: Record<ProductSort, string> = {
  name: 'products.sortName',
  'price-asc': 'products.sortPriceAsc',
  'price-desc': 'products.sortPriceDesc',
};

export function ProductListPage() {
  const { t } = useTranslation();
  const searchId = useId();
  const categoryId = useId();
  const sortId = useId();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [sort, setSort] = useState<ProductSort>(DEFAULT_SORT);
  const [page, setPage] = useState(1);
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
    listProducts({ search, category, page, pageSize: PAGE_SIZE, sort })
      .then((data) => {
        if (!cancelled) setState({ status: 'success', data });
      })
      .catch(() => {
        if (!cancelled) setState({ status: 'error' });
      });
    return () => {
      cancelled = true;
    };
  }, [search, category, sort, page, reloadKey]);

  function onSearchChange(value: string) {
    setSearch(value);
    setPage(1);
  }

  function onCategoryChange(value: string) {
    setCategory(value);
    setPage(1);
  }

  function onSortChange(value: ProductSort) {
    setSort(value);
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
        <label htmlFor={sortId}>{t('products.sortLabel')}</label>
        <select id={sortId} value={sort} onChange={(event) => onSortChange(event.target.value as ProductSort)}>
          {PRODUCT_SORTS.map((value) => (
            <option key={value} value={value}>
              {t(SORT_LABEL_KEYS[value])}
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
          <p className="results-count">{t('products.resultsCount', { count: state.data.totalCount })}</p>
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
