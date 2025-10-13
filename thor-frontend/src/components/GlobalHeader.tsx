import React from 'react';
import { AppBar, Toolbar, Typography, Box, CssBaseline } from '@mui/material';
import CollapsibleDrawer, { DEFAULT_WIDTH_OPEN, DEFAULT_WIDTH_CLOSED } from './CollapsibleDrawer';
import { useLocation } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

const GlobalHeader: React.FC<LayoutProps> = ({ children }) => {
  const [open, setOpen] = React.useState(false);

  const toggleDrawer = () => setOpen((v) => !v);
  const location = useLocation();
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
