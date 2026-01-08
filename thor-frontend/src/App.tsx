// src/App.tsx
import { Routes, Route, Navigate } from 'react-router-dom';

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
// import BrokersPage from './pages/User/Brokers/BrokersPage';
// import SchwabCallbackPage from './pages/User/Brokers/SchwabCallbackPage';

// New Schwab-style homepage
// import Home from './pages/Home/Home';

// NOTE: This App.tsx is the top-level router.
// The visual home page is handled by src/pages/Home/Home.tsx.

function App() {

  return (
    <Routes>
      {/* Public auth routes without app chrome */}
      <Route
        path="/auth/login"
        element={
          <AuthLayout>
            <UserLogin />
          </AuthLayout>
        }
      />
      <Route
        path="/auth/register"
        element={
          <AuthLayout>
            <Register />
          </AuthLayout>
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
                  <Route path="global" element={<GlobalMarkets />} />
                  <Route path="*" element={<Navigate to="global" replace />} />
                </Routes>
              </AppLayout>
            </TradingModeProvider>
          </ProtectedRoute>
        }
      />

      {/* Default */}
      <Route path="/" element={<Navigate to="/auth/login" replace />} />
      <Route path="*" element={<Navigate to="/auth/login" replace />} />
    </Routes>
  );
}

export default App;

