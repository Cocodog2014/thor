import { useState } from 'react'
import { Routes, Route, useLocation, Navigate } from 'react-router-dom'
import { Container } from '@mui/material'
// GlobalHeader is used inside AppLayout only
import GlobalMarkets from './pages/GlobalMarkets/GlobalMarkets'
import FutureTrading from './pages/FutureTrading'
import ActivityPositions from './pages/ActivityPositions'
import AccountStatement from './pages/AccountStatement/AccountStatement'
import ProtectedRoute from './components/ProtectedRoute'
import AuthLayout from './layouts/AuthLayout'
import AppLayout from './layouts/AppLayout'
import Register from './pages/User/Register'
import User, { Login as UserLogin } from './pages/User'
import { TradingModeProvider } from './context/TradingModeContext'

// NOTE: This App.tsx also serves as the home page component
// The HomeContent inline component below handles the home page display
// instead of having a separate Home.tsx file for simplicity
// Removed Heroes, Quests, and Artifacts pages
// Note: App.css and index.css are not used; global resets via MUI CssBaseline, page layout via Home.css

function App() {
  const location = useLocation();
  const [showTradingActivity, setShowTradingActivity] = useState(false);
  const [showAccountStatement, setShowAccountStatement] = useState(false);
  const [showGlobalMarket, setShowGlobalMarket] = useState(true); // Show by default
  const [showFuturesOnHome, setShowFuturesOnHome] = useState(false); // Toggle for split view
  
  // Routes that should have full-width layout (no Container)
  // Ensure both bare paths and /app/* variants are treated as full width
  const fullWidthRoutes = [
    '/', '/home', '/futures',
    '/app/home', '/app/futures'
  ];
  const isFullWidth = fullWidthRoutes.some((p) => location.pathname.startsWith(p));

  const toggleTradingActivity = () => {
    setShowTradingActivity(!showTradingActivity);
  };

  const toggleAccountStatement = () => {
    setShowAccountStatement(!showAccountStatement);
  };

  const toggleGlobalMarket = () => {
    setShowGlobalMarket(!showGlobalMarket);
  };

  const toggleFuturesOnHome = () => {
    setShowFuturesOnHome(!showFuturesOnHome);
  };

  // Inline Home component - split layout with Global Markets + Futures
  const HomeContent = () => (
    <div className="home-screen">
      <div style={{
        display: 'flex',
        gap: '16px',
        alignItems: 'flex-start',
        width: '100%'
      }}>
        {/* Left: Global Markets (fixed width) */}
        {showGlobalMarket && (
          <section className="dashboard-card global-markets" aria-label="Global Markets" style={{
            flexShrink: 0,
            minWidth: '830px', // Ensure table doesn't condense
            width: showFuturesOnHome ? 'auto' : '100%' // Full width when alone, auto when split
          }}>
            <GlobalMarkets />
          </section>
        )}
        
        {/* Right: Futures cards with horizontal scroll */}
        {showFuturesOnHome && (
          <section 
            className="dashboard-card future-trading" 
            aria-label="Futures Trading"
            style={{
              flex: 1,
              overflowX: 'auto',
              overflowY: 'hidden',
              minWidth: 0
            }}
          >
            <FutureTrading />
          </section>
        )}
      </div>

      {/* Additional sections below */}
      <div className="dashboard-grid" style={{ marginTop: showGlobalMarket || showFuturesOnHome ? '16px' : 0 }}>
        {showAccountStatement && (
          <section className="dashboard-card account-statement" aria-label="Account Statement">
            <AccountStatement />
          </section>
        )}
        {showTradingActivity && (
          <section className="dashboard-card activity-positions" aria-label="Activity & Positions">
            <ActivityPositions />
          </section>
        )}
      </div>
    </div>
  );

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
                onAccountStatementToggle={toggleAccountStatement}
                showAccountStatement={showAccountStatement}
                onGlobalMarketToggle={toggleGlobalMarket}
                showGlobalMarket={showGlobalMarket}
                onFuturesOnHomeToggle={toggleFuturesOnHome}
                showFuturesOnHome={showFuturesOnHome}
              >
              {isFullWidth ? (
                <Routes>
                  <Route path="home" element={<HomeContent />} />
                  <Route path="futures" element={<FutureTrading />} />
                  {/* Stock trading removed */}
                  <Route path="user" element={<User />} />
                  <Route path="*" element={<Navigate to="home" replace />} />
                </Routes>
              ) : (
                <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
                  <Routes>
                    <Route path="home" element={<HomeContent />} />
                    <Route path="futures" element={<FutureTrading />} />
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
  )
}

export default App
