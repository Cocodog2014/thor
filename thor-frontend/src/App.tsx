// src/App.tsx
import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';

// GlobalHeader is used inside AppLayout only
import GlobalMarkets from './pages/GlobalMarkets/GlobalMarkets';
// NOTE: MarketSessions removed – no longer used on the home page
// SAFE MODE: keep Futures RTD unmounted to prevent background live hooks.
// import FutureRTD from './pages/Futures';
// Minimal app re-enable: only GlobalMarkets route is active
// import FutureHome from './pages/Futures/FuturesHome/FutureHome';
// import ActivityPositions from './pages/ActivityPositions';
// import Trades from './pages/Trade/Trades';
// import AccountStatement from './pages/AccountStatement/AccountStatement';
import ProtectedRoute from './components/ProtectedRoute';
import AuthLayout from './layouts/AuthLayout';
import AppLayout from './layouts/AppLayout';
import Register from './pages/User/Register';
import { Login as UserLogin } from './pages/User';
import { TradingModeProvider } from './context/TradingModeContext';
import { useAuth } from './context/AuthContext';
// import BrokersPage from './pages/User/Brokers/BrokersPage';
// import SchwabCallbackPage from './pages/User/Brokers/SchwabCallbackPage';

// New Schwab-style homepage
import Home from './pages/Home/Home';

// NOTE: This App.tsx is the top-level router.
// The visual home page is handled by src/pages/Home/Home.tsx.

const AuthIndexRedirect: React.FC = () => {
  const { isAuthenticated } = useAuth();
  return <Navigate to={isAuthenticated ? '/app/home' : '/auth/login'} replace />;
};

const PublicOnlyRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (isAuthenticated) {
    const params = new URLSearchParams(location.search);
    const next = params.get('next');
    const target = next && next.startsWith('/') ? next : '/app/home';
    return <Navigate to={target} replace />;
  }

  return <>{children}</>;
};

function App() {

  return (
    <Routes>
      {/* Public auth routes without app chrome */}
      <Route
        path="/auth/login"
        element={
          <PublicOnlyRoute>
            <AuthLayout>
              <UserLogin />
            </AuthLayout>
          </PublicOnlyRoute>
        }
      />
      <Route
        path="/auth/register"
        element={
          <PublicOnlyRoute>
            <AuthLayout>
              <Register />
            </AuthLayout>
          </PublicOnlyRoute>
        }
      />

      {/* MINIMAL APP: Global Markets only */}
      <Route
        path="/app/*"
        element={
          <ProtectedRoute>
            <TradingModeProvider>
              <AppLayout>
                <Routes>
                  <Route index element={<Navigate to="/app/home" replace />} />
                  <Route path="home" element={<Home />} />
                  <Route path="global" element={<GlobalMarkets />} />
                  <Route path="*" element={<Navigate to="/app/home" replace />} />
                </Routes>
              </AppLayout>
            </TradingModeProvider>
          </ProtectedRoute>
        }
      />

      {/* Default */}
      <Route path="/" element={<AuthIndexRedirect />} />
      <Route path="*" element={<AuthIndexRedirect />} />
    </Routes>
  );
}

export default App;

