import React from 'react';
import { AppBar, Toolbar, Typography, Box, CssBaseline } from '@mui/material';
import CollapsibleDrawer, { DEFAULT_WIDTH_OPEN, DEFAULT_WIDTH_CLOSED } from '../Drawer/CollapsibleDrawer';

interface LayoutProps {
  children: React.ReactNode;
  onTradingActivityToggle?: () => void;
  showTradingActivity?: boolean;
  onGlobalMarketToggle?: () => void;
  showGlobalMarket?: boolean;
  onFuturesOnHomeToggle?: () => void;
  showFuturesOnHome?: boolean;
}

const GlobalHeader: React.FC<LayoutProps> = ({ children, onTradingActivityToggle, showTradingActivity, onGlobalMarketToggle, showGlobalMarket, onFuturesOnHomeToggle, showFuturesOnHome }) => {
  const [open, setOpen] = React.useState(false);

  const toggleDrawer = () => setOpen((v) => !v);

  return (
    <Box sx={{ display: 'flex', position: 'relative' }}>
      <CssBaseline />
      
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: '100%',
          ml: 0,
          background: 'linear-gradient(45deg, #1976d2 30%, #42a5f5 90%)',
          transition: 'margin 200ms ease, width 200ms ease',
          // Place AppBar behind the drawer so there is no visual seam
          zIndex: 1100,
        }}
      >
        <Toolbar sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ width: 160 }} />

          {/* Centered Title */}
          <Typography 
            variant="h4" 
            noWrap 
            component="div" 
            className="header-title"
          >
            ⚡🔨⚡ THOR'S WAR ROOM ⚡🔨⚡
          </Typography>

          <Box sx={{ width: 220 }} />
        </Toolbar>
      </AppBar>

      {/* Sidebar */}
  <CollapsibleDrawer 
    open={open} 
    onToggle={toggleDrawer} 
    widthOpen={DEFAULT_WIDTH_OPEN} 
    widthClosed={DEFAULT_WIDTH_CLOSED}
    onTradingActivityToggle={onTradingActivityToggle}
    showTradingActivity={showTradingActivity}
    onGlobalMarketToggle={onGlobalMarketToggle}
    showGlobalMarket={showGlobalMarket}
    onFuturesOnHomeToggle={onFuturesOnHomeToggle}
    showFuturesOnHome={showFuturesOnHome}
  />

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          bgcolor: 'background.default',
          p: 0,
          // Adjust for AppBar + Banner + Ribbon heights (64 + ~80)
          minHeight: 'calc(100vh - 64px)',
          maxHeight: 'calc(100vh - 64px)',
          overflow: 'hidden',
          transition: 'margin 200ms ease',
          mt: '64px',
          ml: 0,
        }}
      >
        {children}
      </Box>
    </Box>
  );
};

export default GlobalHeader;
