import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

type UserProfile = {
  is_approved?: boolean;
};

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const [approvalState, setApprovalState] = useState<'checking' | 'approved' | 'pending'>('checking');

  useEffect(() => {
    let active = true;

    const check = async () => {
      if (!isAuthenticated) {
        if (active) setApprovalState('checking');
        return;
      }

      try {
        const { data } = await api.get<UserProfile>('/users/profile/');
        if (!active) return;
        setApprovalState(data?.is_approved ? 'approved' : 'pending');
      } catch {
        if (!active) return;
        // If profile fails, treat as not authenticated and let downstream handle.
        setApprovalState('pending');
      }
    };

    check();

    return () => {
      active = false;
    };
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/auth/login?next=${next}`} replace />;
  }

  if (approvalState === 'checking') {
    return null;
  }

  if (approvalState === 'pending') {
    return <Navigate to="/auth/pending-approval" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
