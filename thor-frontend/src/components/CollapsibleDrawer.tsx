import React from 'react';
import {
  Drawer,
  Toolbar,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Box,
} from '@mui/material';
import {
  Home as HomeIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  CandlestickChart as CandlestickChartIcon,
  TrendingUp as TrendingUpIcon,
  AdminPanelSettings as AdminPanelSettingsIcon,
} from '@mui/icons-material';
import { useLocation, useNavigate } from 'react-router-dom';

export interface CollapsibleDrawerProps {
  open: boolean;
  onToggle: () => void;
  widthOpen?: number;
  widthClosed?: number;
}

export const DEFAULT_WIDTH_OPEN = 240;
export const DEFAULT_WIDTH_CLOSED = 72;

const navigationItems = [
  { text: 'Home', icon: <HomeIcon />, path: '/' },
  { text: 'Futures', icon: <TrendingUpIcon />, path: '/futures' },
  { text: 'Stock Trading', icon: <CandlestickChartIcon />, path: '/stock-trading' },
  { text: 'Django Admin', icon: <AdminPanelSettingsIcon />, path: 'http://127.0.0.1:8000/admin/', external: true },
];

const CollapsibleDrawer: React.FC<CollapsibleDrawerProps> = ({
  open,
  onToggle,
  widthOpen = DEFAULT_WIDTH_OPEN,
  widthClosed = DEFAULT_WIDTH_CLOSED,
}) => {
  const location = useLocation();
  const navigate = useNavigate();

  const drawerWidth = open ? widthOpen : widthClosed;

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
        },
      }}
      anchor="left"
    >
      <Toolbar sx={{ display: 'flex', alignItems: 'center', justifyContent: open ? 'space-between' : 'center', px: 1 }}>
        {open && (
          <Typography
            variant="h5"
            sx={{ fontFamily: '"Cinzel", serif', color: '#1976d2', fontWeight: 'bold' }}
          >
            🔨 THOR
          </Typography>
        )}
        <IconButton onClick={onToggle} sx={{ color: '#1976d2' }} aria-label={open ? 'Collapse menu' : 'Expand menu'}>
          {open ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      </Toolbar>

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
      </List>

      {/* small spacer to keep content from hitting bottom on some screens */}
      <Box sx={{ flexGrow: 1 }} />
    </Drawer>
  );
};

export default CollapsibleDrawer;
