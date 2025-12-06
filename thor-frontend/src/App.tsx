// src/App.tsx
import { useState } from 'react';
import { Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { Container } from '@mui/material';

// GlobalHeader is used inside AppLayout only
import GlobalMarkets from './pages/GlobalMarkets/GlobalMarkets';
// NOTE: MarketSessions removed – no longer used on the home page
import FutureRTD from './pages/Futures';
import FutureHome from './pages/Futures/FuturesHome/FutureHome';
import ActivityPositions from './pages/ActivityPositions';
import Trades from './pages/Trade/Trades';
import ProtectedRoute from './components/ProtectedRoute';
import AuthLayout from './layouts/AuthLayout';
import AppLayout from './layouts/AppLayout';
import Register from './pages/User/Register';
import User, { Login as UserLogin } from './pages/User';
import { TradingModeProvider } from './context/TradingModeContext';

// New Schwab-style homepage
import Home from './pages/Home/Home';

// NOTE: This App.tsx is the top-level router.
// The visual home page is handled by src/pages/Home/Home.tsx.

function App() {
  const location = useLocation();

  const [showTradingActivity, setShowTradingActivity] = useState(false);
  const [showGlobalMarket, setShowGlobalMarket] = useState(true); // Show by default
  const [showFuturesOnHome, setShowFuturesOnHome] = useState(true); // Toggle for split view
  const [showMarketOpenDashboard, setShowMarketOpenDashboard] = useState(false); // Market Open Dashboard toggle

  // Routes that should have full-width layout (no Container)
  // Only /app/home needs to be full-width for the Schwab-style dashboard.
  const fullWidthRoutes = ['/app/home', '/app/futures'];
  const isFullWidth = fullWidthRoutes.includes(location.pathname);

  const toggleTradingActivity = () => {
    setShowTradingActivity((prev) => !prev);
  };

  const toggleGlobalMarket = () => {
    setShowGlobalMarket((prev) => !prev);
  };

  const toggleFuturesOnHome = () => {
    setShowFuturesOnHome((prev) => !prev);
  };

  const toggleMarketOpenDashboard = () => {
    setShowMarketOpenDashboard((prev) => !prev);
  };

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

      {/* Protected app routes with app chrome */}
      <Route
        path="/app/*"
        element={
          <ProtectedRoute>
            <TradingModeProvider>
              <AppLayout
                onTradingActivityToggle={toggleTradingActivity}
                showTradingActivity={showTradingActivity}
                onGlobalMarketToggle={toggleGlobalMarket}
                showGlobalMarket={showGlobalMarket}
                onFuturesOnHomeToggle={toggleFuturesOnHome}
                showFuturesOnHome={showFuturesOnHome}
              >
                {isFullWidth ? (
                  // Full-width routes (no MUI Container)
                  <Routes>
                    <Route path="home" element={<Home />} />
                    <Route path="futures" element={<FutureHome />} />
                    {/* Stock trading removed */}
                    <Route path="user" element={<User />} />
                    <Route path="*" element={<Navigate to="home" replace />} />
                  </Routes>
                ) : (
                  // Standard routes wrapped in Container
                  <Container maxWidth={false} sx={{ p: 0 }}>
                    <Routes>
                      <Route path="home" element={<Home />} />
                      <Route path="futures" element={<FutureHome />} />
                      <Route
                        path="futures/rtd"
                        element={
                          <FutureRTD
                            onToggleMarketOpen={toggleMarketOpenDashboard}
                            showMarketOpen={showMarketOpenDashboard}
                          />
                        }
                      />
                      <Route path="global" element={<GlobalMarkets />} />
                      <Route path="trade" element={<Trades />} />
                      <Route path="activity" element={<ActivityPositions />} />
                      {/* Stock trading removed */}
                      <Route path="user" element={<User />} />
                      <Route path="*" element={<Navigate to="home" replace />} />
                    </Routes>
                  </Container>
                )}
              </AppLayout>
            </TradingModeProvider>
          </ProtectedRoute>
        }
      />

      {/* Default redirect: root to /app/home */}
      <Route path="/" element={<Navigate to="/app/home" replace />} />
      <Route path="*" element={<Navigate to="/app/home" replace />} />
    </Routes>
  );
}

export default App;

