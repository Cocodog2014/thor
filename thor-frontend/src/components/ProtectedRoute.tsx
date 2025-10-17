import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';

const hasToken = () => {
  try {
    // Check for JWT access token (stored by Login.tsx)
    return !!localStorage.getItem('thor_access_token');
  } catch {
    return false;
  }
};

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  if (!hasToken()) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/auth/login?next=${next}`} replace />;
  }
  return <>{children}</>;
};

export default ProtectedRoute;
