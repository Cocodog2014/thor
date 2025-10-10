import React from 'react';
import { AppBar, Toolbar, Typography, Box, CssBaseline, Button } from '@mui/material';
import CollapsibleDrawer, { DEFAULT_WIDTH_OPEN, DEFAULT_WIDTH_CLOSED } from './CollapsibleDrawer';
import { useLocation } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

const GlobalHeader: React.FC<LayoutProps> = ({ children }) => {
  const [open, setOpen] = React.useState(false);
  const [activeProvider, setActiveProvider] = React.useState(
    localStorage.getItem('selectedProvider') || 'excel_live'
  );
  
  const toggleDrawer = () => setOpen((v) => !v);
  const location = useLocation();
  
  const selectProvider = (provider: string) => {
    setActiveProvider(provider);
    localStorage.setItem('selectedProvider', provider);
    
    window.dispatchEvent(new CustomEvent('provider-changed', { 
      detail: { provider } 
    }));
  };
  const fullWidthRoutes = ['/', '/home', '/futures'];
  const isFullWidth = fullWidthRoutes.includes(location.pathname);

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: `calc(100% - ${(open ? DEFAULT_WIDTH_OPEN : DEFAULT_WIDTH_CLOSED)}px)`,
          ml: `${open ? DEFAULT_WIDTH_OPEN : DEFAULT_WIDTH_CLOSED}px`,
          background: 'linear-gradient(45deg, #1976d2 30%, #42a5f5 90%)',
          transition: 'margin 200ms ease, width 200ms ease',
        }}
      >
        <Toolbar sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
          {/* Data Source Section */}
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant={activeProvider === 'excel_live' ? 'contained' : 'outlined'}
              size="small"
              onClick={() => selectProvider('excel_live')}
              sx={{
                color: activeProvider === 'excel_live' ? 'white' : 'white',
                borderColor: 'white',
                '&.MuiButton-contained': {
                  backgroundColor: '#4caf50', // Green when active
                  '&:hover': {
                    backgroundColor: '#45a049',
                  }
                },
                '&.MuiButton-outlined': {
                  borderColor: 'rgba(255, 255, 255, 0.5)',
                  '&:hover': {
                    borderColor: 'rgba(255, 255, 255, 0.8)',
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  }
                },
              }}
            >
              EXCEL LIVE
            </Button>
            <Button
              variant={activeProvider === 'schwab' ? 'contained' : 'outlined'}
              size="small"
              onClick={() => selectProvider('schwab')}
              sx={{
                color: activeProvider === 'schwab' ? 'white' : 'white',
                borderColor: 'white',
                '&.MuiButton-contained': {
                  backgroundColor: '#4caf50', // Green when active
                  '&:hover': {
                    backgroundColor: '#45a049',
                  }
                },
                '&.MuiButton-outlined': {
                  borderColor: 'rgba(255, 255, 255, 0.5)',
                  '&:hover': {
                    borderColor: 'rgba(255, 255, 255, 0.8)',
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  }
                },
              }}
            >
              SCHWAB
            </Button>
          </Box>

          {/* Centered Title */}
          <Typography 
            variant="h4" 
            noWrap 
            component="div" 
            sx={{ 
              fontFamily: '"Cinzel", serif',
              fontSize: '2.25rem',
              position: 'absolute',
              left: '50%',
              transform: 'translateX(-50%)',
            }}
          >
            Thor War Room
          </Typography>

          {/* Empty space for balance */}
          <Box sx={{ width: 'auto' }} />
        </Toolbar>
      </AppBar>

      {/* Sidebar */}
  <CollapsibleDrawer open={open} onToggle={toggleDrawer} widthOpen={DEFAULT_WIDTH_OPEN} widthClosed={DEFAULT_WIDTH_CLOSED} />

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'background.default',
          p: isFullWidth ? 0 : 3,
          minHeight: '100vh',
          transition: 'margin 200ms ease',
        }}
      >
        <Toolbar disableGutters sx={{ pl: 0, pr: 0 }} />
        {children}
      </Box>
    </Box>
  );
};

export default GlobalHeader;
