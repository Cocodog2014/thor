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
}

export const DEFAULT_WIDTH_OPEN = 240;
export const DEFAULT_WIDTH_CLOSED = 72;

const navigationItems = [
  { text: 'Home', icon: <HomeIcon />, path: '/app/home' },
  { text: 'Futures', icon: <TrendingUpIcon />, path: '/app/futures' },
  { text: 'Django Admin', icon: <AdminPanelSettingsIcon />, path: 'http://127.0.0.1:8000/admin/', external: true },
];

const CollapsibleDrawer: React.FC<CollapsibleDrawerProps> = ({
  open,
  onToggle,
  widthOpen = DEFAULT_WIDTH_OPEN,
  widthClosed = DEFAULT_WIDTH_CLOSED,
  onTradingActivityToggle,
  showTradingActivity = false,
  onAccountStatementToggle,
  showAccountStatement = false,
}) => {
  const location = useLocation();
  const navigate = useNavigate();

  const drawerWidth = open ? widthOpen : widthClosed;

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
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        whiteSpace: 'nowrap',
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
          overflowX: 'hidden',
          transition: 'width 200ms ease',
          background: 'linear-gradient(180deg, #1a1f2e 0%, #0a0e13 100%)',
          borderRight: 'none', // Remove default MUI paper right border/seam
        },
      }}
      anchor="left"
    >
      <Toolbar sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', px: 1 }}>
        <IconButton onClick={onToggle} sx={{ color: '#1976d2' }} aria-label={open ? 'Collapse menu' : 'Expand menu'}>
          {open ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      </Toolbar>

      {/* Account Information Section */}
      {open && (
        <>
          <Box sx={{ px: 2, py: 1 }}>
            <Typography variant="subtitle2" sx={{ color: '#1976d2', fontWeight: 'bold', mb: 1 }}>
              Account Info
            </Typography>
            <Box sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Option Buying Power</span>
                <span style={{ color: '#4caf50' }}>$301.95</span>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Net Liq & Day Trades</span>
                <span style={{ color: '#4caf50' }}>$86,081.37</span>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Day Trading Buying Power</span>
                <span style={{ color: '#4caf50' }}>$301.95</span>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Day Trades Left</span>
                <span style={{ color: '#ff9800' }}>3</span>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <span>Cash & Sweep Vehicle</span>
                <span style={{ color: '#4caf50' }}>$301.95</span>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Available Funds For Trading</span>
                <span style={{ color: '#4caf50' }}>$301.95</span>
              </Box>
            </Box>
          </Box>
          <Divider sx={{ mx: 1 }} />
        </>
      )}

      <List>
        {navigationItems.map((item) => (
          <ListItem key={item.text} disablePadding sx={{ display: 'block' }}>
            <ListItemButton
              selected={!item.external && location.pathname === item.path}
              onClick={() => {
                if (item.external) {
                  window.open(item.path, '_blank', 'noopener,noreferrer');
                  return;
                }
                navigate(item.path);
              }}
              sx={{
                minHeight: 48,
                justifyContent: open ? 'initial' : 'center',
                px: 2.5,
                '&.Mui-selected': {
                  backgroundColor: 'rgba(25, 118, 210, 0.2)',
                  borderRight: '3px solid #1976d2',
                },
                '&:hover': {
                  backgroundColor: 'rgba(25, 118, 210, 0.1)',
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 0, mr: open ? 3 : 'auto', justifyContent: 'center', color: '#1976d2' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} sx={{ opacity: open ? 1 : 0, color: '#fff' }} />
            </ListItemButton>
          </ListItem>
        ))}

        {/* Accounts & Statements Toggle (appears high in the list) */}
        <ListItem disablePadding sx={{ display: 'block' }}>
          <ListItemButton
            selected={showAccountStatement}
            onClick={onAccountStatementToggle}
            sx={{
              minHeight: 48,
              justifyContent: open ? 'initial' : 'center',
              px: 2.5,
              '&.Mui-selected': {
                backgroundColor: 'rgba(25, 118, 210, 0.2)',
                borderRight: '3px solid #1976d2',
              },
              '&:hover': {
                backgroundColor: 'rgba(25, 118, 210, 0.1)',
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 0, mr: open ? 3 : 'auto', justifyContent: 'center', color: '#1976d2' }}>
              <ReceiptLongIcon />
            </ListItemIcon>
            <ListItemText primary="Accounts & Statements" sx={{ opacity: open ? 1 : 0, color: '#fff' }} />
          </ListItemButton>
        </ListItem>
        
  {/* Trading Activity Toggle */}
        <ListItem disablePadding sx={{ display: 'block' }}>
          <ListItemButton
            selected={showTradingActivity}
            onClick={onTradingActivityToggle}
            sx={{
              minHeight: 48,
              justifyContent: open ? 'initial' : 'center',
              px: 2.5,
              '&.Mui-selected': {
                backgroundColor: 'rgba(25, 118, 210, 0.2)',
                borderRight: '3px solid #1976d2',
              },
              '&:hover': {
                backgroundColor: 'rgba(25, 118, 210, 0.1)',
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 0, mr: open ? 3 : 'auto', justifyContent: 'center', color: '#1976d2' }}>
              <TradingActivityIcon />
            </ListItemIcon>
            <ListItemText primary="Trading Activity" sx={{ opacity: open ? 1 : 0, color: '#fff' }} />
          </ListItemButton>
        </ListItem>
      </List>

      {/* Sign out at bottom */}
      <Box sx={{ flexGrow: 1 }} />
      <List>
        <ListItem disablePadding sx={{ display: 'block' }}>
          <ListItemButton
            onClick={signOut}
            sx={{
              minHeight: 48,
              justifyContent: open ? 'initial' : 'center',
              px: 2.5,
              '&:hover': {
                backgroundColor: 'rgba(25, 118, 210, 0.1)',
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 0, mr: open ? 3 : 'auto', justifyContent: 'center', color: '#1976d2' }}>
              <LogoutIcon />
            </ListItemIcon>
            <ListItemText primary="Sign out" sx={{ opacity: open ? 1 : 0, color: '#fff' }} />
          </ListItemButton>
        </ListItem>
      </List>
    </Drawer>
  );
};

export default CollapsibleDrawer;
