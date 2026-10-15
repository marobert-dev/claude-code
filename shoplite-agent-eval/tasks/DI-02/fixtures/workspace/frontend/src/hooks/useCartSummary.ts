import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { getCartSummary } from '../api/cart';
import type { CartSummary } from '../api/types';

export function useCartSummary(enabled: boolean): CartSummary | null {
  const location = useLocation();
  const [summary, setSummary] = useState<CartSummary | null>(null);

  useEffect(() => {
    if (!enabled) {
      setSummary(null);
      return;
    }
    let cancelled = false;
    getCartSummary()
      .then((result) => {
        if (!cancelled) setSummary(result);
      })
      .catch(() => {
        if (!cancelled) setSummary(null);
      });
    return () => {
      cancelled = true;
    };
  }, [enabled, location.pathname]);

  return summary;
}
