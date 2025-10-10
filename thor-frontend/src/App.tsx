import { Routes, Route, useLocation } from 'react-router-dom'
import { Container } from '@mui/material'
import GlobalHeader from './components/GlobalHeader.tsx'
import TimeZone from './pages/TimeZone/TimeZone.tsx'
import FutureTrading from './pages/FutureTrading'
import StockTrading from './pages/StockTrading'

// NOTE: This App.tsx also serves as the home page component
// The HomeContent inline component below handles the home page display
// instead of having a separate Home.tsx file for simplicity
// Removed Heroes, Quests, and Artifacts pages
// Note: App.css and index.css are not used; global resets via MUI CssBaseline, page layout via Home.css

function App() {
  const location = useLocation();
  
  // Routes that should have full-width layout (no Container)
  const fullWidthRoutes = ['/', '/home', '/futures', '/stock-trading'];
  const isFullWidth = fullWidthRoutes.includes(location.pathname);

  // Inline Home component - just the TimeZone display
  const HomeContent = () => (
    <div className="dashboard-grid">
      <section className="dashboard-card global-markets" aria-label="Global Markets">
        <TimeZone />
      </section>
    </div>
  );

  return (
    <GlobalHeader>
      {isFullWidth ? (
        <Routes>
          <Route path="/" element={<HomeContent />} />
          <Route path="/home" element={<HomeContent />} />
          <Route path="/futures" element={<FutureTrading />} />
          <Route path="/stock-trading" element={<StockTrading />} />
        </Routes>
      ) : (
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
          <Routes>
            <Route path="/" element={<HomeContent />} />
            <Route path="/home" element={<HomeContent />} />
            <Route path="/futures" element={<FutureTrading />} />
            <Route path="/stock-trading" element={<StockTrading />} />
          </Routes>
        </Container>
      )}
    </GlobalHeader>
  )
}

export default App
