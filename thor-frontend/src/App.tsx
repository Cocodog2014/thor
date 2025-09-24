import { Routes, Route, useLocation } from 'react-router-dom'
import { Container } from '@mui/material'
import GlobalHeader from './components/GlobalHeader.tsx'
import Home from './pages/home/Home.tsx'
import FutureTrading from './pages/FutureTrading'
// Removed Heroes, Quests, and Artifacts pages
// Note: App.css and index.css are not used; global resets via MUI CssBaseline, page layout via Home.css

function App() {
  const location = useLocation();
  
  // Routes that should have full-width layout (no Container)
  const fullWidthRoutes = ['/', '/home', '/futures'];
  const isFullWidth = fullWidthRoutes.includes(location.pathname);

  return (
    <GlobalHeader>
      {isFullWidth ? (
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/home" element={<Home />} />
          <Route path="/futures" element={<FutureTrading />} />
        </Routes>
      ) : (
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/home" element={<Home />} />
            <Route path="/futures" element={<FutureTrading />} />
          </Routes>
        </Container>
      )}
    </GlobalHeader>
  )
}

export default App
