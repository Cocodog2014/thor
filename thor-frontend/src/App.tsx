import { useState } from 'react'
import { Routes, Route, useLocation, Navigate } from 'react-router-dom'
import { Container } from '@mui/material'
// GlobalHeader is used inside AppLayout only
import TimeZone from './pages/TimeZone/TimeZone.tsx'
import FutureTrading from './pages/FutureTrading'
import StockTrading from './pages/StockTrading'
import ActivityPositions from './pages/ActivityPositions'
import ProtectedRoute from './components/ProtectedRoute'
import AuthLayout from './layouts/AuthLayout'
import AppLayout from './layouts/AppLayout'
import Register from './pages/User/Register'
import User, { Login as UserLogin } from './pages/User'

// NOTE: This App.tsx also serves as the home page component
// The HomeContent inline component below handles the home page display
// instead of having a separate Home.tsx file for simplicity
// Removed Heroes, Quests, and Artifacts pages
// Note: App.css and index.css are not used; global resets via MUI CssBaseline, page layout via Home.css

function App() {
  const location = useLocation();
  const [showTradingActivity, setShowTradingActivity] = useState(false);
  
  // Routes that should have full-width layout (no Container)
  const fullWidthRoutes = ['/', '/home', '/futures', '/stock-trading'];
  const isFullWidth = fullWidthRoutes.includes(location.pathname);

  const toggleTradingActivity = () => {
    setShowTradingActivity(!showTradingActivity);
  };

  // Inline Home component - just the TimeZone display
  const HomeContent = () => (
    <div className="dashboard-grid">
      <section className="dashboard-card global-markets" aria-label="Global Markets">
        <TimeZone />
      </section>
      {showTradingActivity && (
        <section className="dashboard-card activity-positions" aria-label="Activity & Positions">
          <ActivityPositions />
        </section>
      )}
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
            <AppLayout onTradingActivityToggle={toggleTradingActivity} showTradingActivity={showTradingActivity}>
              {isFullWidth ? (
                <Routes>
                  <Route path="home" element={<HomeContent />} />
                  <Route path="futures" element={<FutureTrading />} />
                  <Route path="stock-trading" element={<StockTrading />} />
                  <Route path="user" element={<User />} />
                  <Route path="*" element={<Navigate to="home" replace />} />
                </Routes>
              ) : (
                <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
                  <Routes>
                    <Route path="home" element={<HomeContent />} />
                    <Route path="futures" element={<FutureTrading />} />
                    <Route path="stock-trading" element={<StockTrading />} />
                    <Route path="user" element={<User />} />
                    <Route path="*" element={<Navigate to="home" replace />} />
                  </Routes>
                </Container>
              )}
            </AppLayout>
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
