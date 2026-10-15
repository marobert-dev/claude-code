import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, useLocation } from 'react-router-dom';
import type { LoginResponse } from '../api/types';
import { useAuth } from '../auth/AuthContext';

interface RequireAuthProps {
  children: ReactNode;
  role?: LoginResponse['role'];
}

export function RequireAuth({ children, role }: RequireAuthProps) {
  const { session } = useAuth();
  const location = useLocation();
  const { t } = useTranslation();

  if (!session) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (role && session.role !== role) {
    return <h1>{t('common.notFound')}</h1>;
  }
  return children;
}
