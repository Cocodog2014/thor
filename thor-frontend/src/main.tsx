import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import App from './App.tsx'
import theme from './theme'
import './styles/global.css'
import { AuthProvider } from './context/AuthContext'
import { GlobalTimerProvider } from './context/GlobalTimerContext'
import { SelectedAccountProvider } from './context/SelectedAccountContext'
import { RealTimeProvider } from './realtime/RealTimeProvider'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 0,
      refetchOnMount: 'always',
      keepPreviousData: false,
    },
  },
})

// Theme moved to src/theme.ts to centralize colors/typography

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <AuthProvider>
            <SelectedAccountProvider>
              <RealTimeProvider>
                <GlobalTimerProvider>
                  <App />
                </GlobalTimerProvider>
              </RealTimeProvider>
            </SelectedAccountProvider>
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
