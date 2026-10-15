import { useId, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import type { Product, ProductUpsertRequest } from '../api/types';

interface ProductFormProps {
  title: string;
  initial?: Product;
  onSubmit: (request: ProductUpsertRequest) => void;
  onCancel: () => void;
}

type FieldErrors = Partial<Record<'name' | 'category' | 'price' | 'stock', string>>;

function validate(values: ProductUpsertRequest, t: (key: string) => string): FieldErrors {
  const errors: FieldErrors = {};
  if (values.name.trim() === '') errors.name = t('admin.nameRequired');
  if (values.category.trim() === '') errors.category = t('admin.categoryRequired');
  if (!(values.price > 0)) errors.price = t('admin.priceInvalid');
  if (!Number.isInteger(values.stock) || values.stock < 0) errors.stock = t('admin.stockInvalid');
  return errors;
}

export function ProductForm({ title, initial, onSubmit, onCancel }: ProductFormProps) {
  const { t } = useTranslation();
  const baseId = useId();
  const [values, setValues] = useState<ProductUpsertRequest>({
    name: initial?.name ?? '',
    description: initial?.description ?? '',
    category: initial?.category ?? '',
    price: initial?.price ?? 0,
    stock: initial?.stock ?? 0,
  });
  const [errors, setErrors] = useState<FieldErrors>({});

  function update<K extends keyof ProductUpsertRequest>(field: K, value: ProductUpsertRequest[K]) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const found = validate(values, t);
    setErrors(found);
    if (Object.keys(found).length === 0) onSubmit(values);
  }

  const fieldId = (name: string) => `${baseId}-${name}`;
  const errorProps = (name: keyof FieldErrors) =>
    errors[name] ? { 'aria-invalid': true, 'aria-describedby': `${fieldId(name)}-error` } : {};
  const errorText = (name: keyof FieldErrors) =>
    errors[name] && (
      <p id={`${fieldId(name)}-error`} className="field-error">
        {errors[name]}
      </p>
    );

  return (
    <form noValidate onSubmit={handleSubmit} className="product-form" aria-labelledby={fieldId('title')}>
      <h2 id={fieldId('title')}>{title}</h2>
      <label htmlFor={fieldId('name')}>{t('admin.name')}</label>
      <input id={fieldId('name')} value={values.name} onChange={(e) => update('name', e.target.value)} {...errorProps('name')} />
      {errorText('name')}

      <label htmlFor={fieldId('description')}>{t('admin.description')}</label>
      <textarea id={fieldId('description')} value={values.description} onChange={(e) => update('description', e.target.value)} />

      <label htmlFor={fieldId('category')}>{t('admin.category')}</label>
      <input id={fieldId('category')} value={values.category} onChange={(e) => update('category', e.target.value)} {...errorProps('category')} />
      {errorText('category')}

      <label htmlFor={fieldId('price')}>{t('admin.price')}</label>
      <input
        id={fieldId('price')}
        type="number"
        step="0.01"
        value={values.price}
        onChange={(e) => update('price', Number(e.target.value))}
        {...errorProps('price')}
      />
      {errorText('price')}

      <label htmlFor={fieldId('stock')}>{t('admin.stock')}</label>
      <input
        id={fieldId('stock')}
        type="number"
        step="1"
        value={values.stock}
        onChange={(e) => update('stock', Number(e.target.value))}
        {...errorProps('stock')}
      />
      {errorText('stock')}

      <div className="form-actions">
        <button type="button" onClick={onCancel}>
          {t('admin.cancel')}
        </button>
        <button type="submit" className="primary">
          {t('admin.save')}
        </button>
      </div>
    </form>
  );
}
