import React from 'react';
import {
  Drawer,
  Toolbar,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Box,
  Typography,
  Divider,
} from '@mui/material';
import {
  Home as HomeIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  TrendingUp as TrendingUpIcon,
  AdminPanelSettings as AdminPanelSettingsIcon,
  AccountBalance as TradingActivityIcon,
  Logout as LogoutIcon,
  Public as PublicIcon,
} from '@mui/icons-material';
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong';
import { useLocation, useNavigate } from 'react-router-dom';

export interface CollapsibleDrawerProps {
  open: boolean;
  onToggle: () => void;
  widthOpen?: number;
  widthClosed?: number;
  onTradingActivityToggle?: () => void;
  showTradingActivity?: boolean;
  onAccountStatementToggle?: () => void;
  showAccountStatement?: boolean;
  onGlobalMarketToggle?: () => void;
  showGlobalMarket?: boolean;
  onFuturesOnHomeToggle?: () => void;
  showFuturesOnHome?: boolean;
}

export const DEFAULT_WIDTH_OPEN = 240;
export const DEFAULT_WIDTH_CLOSED = 72;

const navigationItems = [
  { text: 'Home', icon: <HomeIcon />, path: '/app/home' },
  // Removed problematic 'Futures' direct route; use 'Futures on Home' toggle below instead
  { text: 'Django Admin', icon: <AdminPanelSettingsIcon />, path: 'http://127.0.0.1:8000/admin/', external: true },
];

const CollapsibleDrawer: React.FC<CollapsibleDrawerProps> = ({
  open,
  onToggle,
  // widthOpen = DEFAULT_WIDTH_OPEN,
  // widthClosed = DEFAULT_WIDTH_CLOSED,
  onTradingActivityToggle,
  showTradingActivity = false,
  onAccountStatementToggle,
  showAccountStatement = false,
  onGlobalMarketToggle,
  showGlobalMarket = false,
  onFuturesOnHomeToggle,
  showFuturesOnHome = false,
}) => {
  const location = useLocation();
  const navigate = useNavigate();

  // Width is now controlled via CSS classes; constants kept for GlobalHeader layout.

  const signOut = () => {
    try {
      localStorage.removeItem('thor_access_token');
      localStorage.removeItem('thor_refresh_token');
    } catch {}
    navigate('/auth/login');
  };

  return (
    <Drawer
      variant="permanent"
      anchor="left"
      className={`thor-drawer ${open ? 'open' : 'closed'}`}
    >
      <Toolbar sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', px: 1 }}>
        <IconButton onClick={onToggle} className="thor-drawer-toggle" aria-label={open ? 'Collapse menu' : 'Expand menu'}>
          {open ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      </Toolbar>

      {/* Account Information Section */}
      {open && (
        <>
          <Box sx={{ px: 2, py: 1 }}>
            <Typography variant="subtitle2" className="thor-account-title" sx={{ mb: 1 }}>
              Account Info
            </Typography>
            <Box sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Option Buying Power</span>
                <Box component="span" sx={{ color: '#4caf50' }}>$301.95</Box>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Net Liq & Day Trades</span>
                <Box component="span" sx={{ color: '#4caf50' }}>$86,081.37</Box>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Day Trading Buying Power</span>
                <Box component="span" sx={{ color: '#4caf50' }}>$301.95</Box>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Day Trades Left</span>
                <Box component="span" sx={{ color: '#ff9800' }}>3</Box>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Cash & Sweep Vehicle</span>
                <Box component="span" sx={{ color: '#4caf50' }}>$301.95</Box>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Available Funds For Trading</span>
                <Box component="span" sx={{ color: '#4caf50' }}>$301.95</Box>
              </Box>
            </Box>
          </Box>
          <Divider sx={{ mx: 1 }} />
        </>
      )}

      <List>
        {navigationItems.map((item) => {
          const selected = !item.external && location.pathname.startsWith(item.path);
          return (
            <ListItem key={item.text} disablePadding sx={{ display: 'block' }}>
              <ListItemButton
                className="thor-nav-button"
                selected={selected}
                onClick={() => {
                  if (item.external) {
                    window.open(item.path, '_blank', 'noopener,noreferrer');
                    return;
                  }
                  navigate(item.path);
                }}
            >
              <ListItemIcon className="thor-nav-icon">
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} className="thor-nav-text" />
            </ListItemButton>
          </ListItem>
        );})}

        {/* Global Market (TimeZone) Toggle */}
        <ListItem disablePadding sx={{ display: 'block' }}>
          <ListItemButton
            className="thor-nav-button"
            selected={showGlobalMarket}
            onClick={onGlobalMarketToggle}
          >
            <ListItemIcon className="thor-nav-icon">
              <PublicIcon />
            </ListItemIcon>
            <ListItemText primary="Global Market" className="thor-nav-text" />
          </ListItemButton>
        </ListItem>

        {/* Futures card toggle for home dashboard */}
        <ListItem disablePadding sx={{ display: 'block' }}>
          <ListItemButton
            className="thor-nav-button"
            selected={showFuturesOnHome}
            onClick={onFuturesOnHomeToggle}
          >
            <ListItemIcon className="thor-nav-icon">
              <TrendingUpIcon />
            </ListItemIcon>
            <ListItemText primary="Futures on Home" className="thor-nav-text" />
          </ListItemButton>
        </ListItem>

        {/* Accounts & Statements Toggle (appears high in the list) */}
        <ListItem disablePadding sx={{ display: 'block' }}>
          <ListItemButton
            className="thor-nav-button"
            selected={showAccountStatement}
            onClick={onAccountStatementToggle}
          >
            <ListItemIcon className="thor-nav-icon">
              <ReceiptLongIcon />
            </ListItemIcon>
            <ListItemText primary="Accounts & Statements" className="thor-nav-text" />
          </ListItemButton>
        </ListItem>
        
  {/* Trading Activity Toggle */}
        <ListItem disablePadding sx={{ display: 'block' }}>
          <ListItemButton
            className="thor-nav-button"
            selected={showTradingActivity}
            onClick={onTradingActivityToggle}
          >
            <ListItemIcon className="thor-nav-icon">
              <TradingActivityIcon />
            </ListItemIcon>
            <ListItemText primary="Trading Activity" className="thor-nav-text" />
          </ListItemButton>
        </ListItem>
      </List>

      {/* Sign out at bottom */}
      <Box sx={{ flexGrow: 1 }} />
      <List>
        <ListItem disablePadding sx={{ display: 'block' }}>
          <ListItemButton
            onClick={signOut}
            className="thor-nav-button"
          >
            <ListItemIcon className="thor-nav-icon">
              <LogoutIcon />
            </ListItemIcon>
            <ListItemText primary="Sign out" className="thor-nav-text" />
          </ListItemButton>
        </ListItem>
      </List>
    </Drawer>
  );
};

export default CollapsibleDrawer;
