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
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  AdminPanelSettings as AdminPanelSettingsIcon,
  Logout as LogoutIcon,
} from '@mui/icons-material';
import { useLocation, useNavigate } from 'react-router-dom';
import { HOME_WELCOME_DISMISSED_KEY } from '../../constants/storageKeys';
import { useAuth } from '../../context/AuthContext';

export interface CollapsibleDrawerProps {
  open: boolean;
  onToggle: () => void;
  widthOpen?: number;
  widthClosed?: number;
}

export const DEFAULT_WIDTH_OPEN = 240;
export const DEFAULT_WIDTH_CLOSED = 72;

const navigationItems = [
  { text: 'Django Admin', icon: <AdminPanelSettingsIcon />, path: 'http://127.0.0.1:8000/admin/', external: true },
];

const CollapsibleDrawer: React.FC<CollapsibleDrawerProps> = ({
  open,
  onToggle,
  // widthOpen = DEFAULT_WIDTH_OPEN,
  // widthClosed = DEFAULT_WIDTH_CLOSED,
}) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout } = useAuth();

  // Width is now controlled via CSS classes; constants kept for GlobalHeader layout.

  const signOut = () => {
    logout();
    try {
      sessionStorage.removeItem(HOME_WELCOME_DISMISSED_KEY);
    } catch {
      // Ignore sessionStorage errors
    }
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
