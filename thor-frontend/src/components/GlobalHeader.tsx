import React from 'react';
import { AppBar, Toolbar, Typography, Box, CssBaseline } from '@mui/material';
import CollapsibleDrawer, { DEFAULT_WIDTH_OPEN, DEFAULT_WIDTH_CLOSED } from './CollapsibleDrawer';

interface LayoutProps {
  children: React.ReactNode;
  onTradingActivityToggle?: () => void;
  showTradingActivity?: boolean;
}

const GlobalHeader: React.FC<LayoutProps> = ({ children, onTradingActivityToggle, showTradingActivity }) => {
  const [open, setOpen] = React.useState(false);

  const toggleDrawer = () => setOpen((v) => !v);

  return (
    <Box sx={{ display: 'flex', position: 'relative' }}>
      <CssBaseline />
      
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: `calc(100% - ${(open ? DEFAULT_WIDTH_OPEN : DEFAULT_WIDTH_CLOSED)}px)`,
          ml: `${open ? DEFAULT_WIDTH_OPEN : DEFAULT_WIDTH_CLOSED}px`,
          background: 'linear-gradient(45deg, #1976d2 30%, #42a5f5 90%)',
          transition: 'margin 200ms ease, width 200ms ease',
          zIndex: 1200,
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

          {/* Empty space for balance */}
          <Box sx={{ width: 160, display: 'flex', justifyContent: 'flex-end' }} />
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
  />

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'background.default',
          p: 0,
          minHeight: '100vh',
          transition: 'margin 200ms ease',
          pt: '64px', // Clear fixed header height
        }}
      >
        {children}
      </Box>
    </Box>
  );
};

export default GlobalHeader;
