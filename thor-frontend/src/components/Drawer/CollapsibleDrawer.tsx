import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWsConnection, wsEnabled } from '../../realtime';
import {
  Box,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
} from '@mui/material';
import {
  AdminPanelSettings as AdminPanelSettingsIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Logout as LogoutIcon,
} from '@mui/icons-material';
import { useAuth } from '../../context/AuthContext';
import { HOME_WELCOME_DISMISSED_KEY } from '../../constants/storageKeys';
import Watchlist from './Watchlist';

export const DEFAULT_WIDTH_OPEN = 450;
export const DEFAULT_WIDTH_CLOSED = 72;
const MIN_DRAWER_WIDTH = 100;
const MAX_DRAWER_WIDTH = 600;

const navigationItems = [
  { text: 'Django Admin', icon: <AdminPanelSettingsIcon />, path: 'http://127.0.0.1:8000/admin/', external: true },
];

export interface CollapsibleDrawerProps {
  open: boolean;
  onToggle: () => void;
  widthOpen?: number;
  widthClosed?: number;
  storageKey?: string;
}

const CollapsibleDrawer: React.FC<CollapsibleDrawerProps> = ({
  open,
  onToggle,
  widthOpen = DEFAULT_WIDTH_OPEN,
  widthClosed = DEFAULT_WIDTH_CLOSED,
  storageKey,
}) => {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const [drawerWidth, setDrawerWidth] = useState(widthOpen);
  const [isResizing, setIsResizing] = useState(false);
  const resizeState = useRef({ startX: 0, startWidth: drawerWidth });

  const wsIsEnabled = wsEnabled();
  const wsConnected = useWsConnection(true);
  const [lastTickAt, setLastTickAt] = useState<Date | null>(null);

  useEffect(() => {
    if (!storageKey || typeof window === 'undefined') {
      return;
    }

    try {
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) return;
      const parsed = JSON.parse(raw) as { width?: unknown };
      const savedWidth = typeof parsed?.width === 'number' ? parsed.width : undefined;
      if (savedWidth !== undefined && Number.isFinite(savedWidth)) {
        setDrawerWidth(Math.min(MAX_DRAWER_WIDTH, Math.max(MIN_DRAWER_WIDTH, savedWidth)));
      }
    } catch {
      // ignore storage parse errors
    }
  }, [storageKey]);

  useEffect(() => {
    if (!storageKey || typeof window === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem(storageKey, JSON.stringify({ open, width: drawerWidth }));
    } catch {
      // ignore storage write errors
    }
  }, [drawerWidth, open, storageKey]);

  const handleResizeMouseDown = (e: React.MouseEvent) => {
    setIsResizing(true);
    resizeState.current = { startX: e.clientX, startWidth: drawerWidth };
  };

  useEffect(() => {
    if (!isResizing) return;

    const onMove = (e: MouseEvent) => {
      const delta = e.clientX - resizeState.current.startX;
      setDrawerWidth(
        Math.min(
          MAX_DRAWER_WIDTH,
          Math.max(MIN_DRAWER_WIDTH, resizeState.current.startWidth + delta)
        )
      );
    };

    const onUp = () => setIsResizing(false);

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [isResizing]);

  const signOut = () => {
    logout();
    sessionStorage.removeItem(HOME_WELCOME_DISMISSED_KEY);
    navigate('/auth/login');
  };

  const currentWidth = open ? drawerWidth : widthClosed;

  const wsStatusLabel = wsIsEnabled ? (wsConnected ? 'WS: Connected' : 'WS: Disconnected') : 'WS: Disabled';
  const wsStatusColor = !wsIsEnabled ? 'text.secondary' : wsConnected ? '#4caf50' : '#f44336';
  const wsLastTickLabel = lastTickAt ? ` · last tick ${lastTickAt.toLocaleTimeString('en-US')}` : '';

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: currentWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: currentWidth,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          transition: isResizing ? 'none' : 'width 0.2s',
          backgroundColor: '#000',
        },
      }}
    >
      <Toolbar sx={{ justifyContent: open ? 'space-between' : 'center', px: 1 }}>
        {open && (
          <Typography
            variant="caption"
            sx={{
              color: wsStatusColor,
              fontWeight: 600,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              maxWidth: '75%',
            }}
            title={`${wsStatusLabel}${wsLastTickLabel}`}
          >
            {wsStatusLabel}{wsLastTickLabel}
          </Typography>
        )}

        <IconButton onClick={onToggle}>{open ? <ChevronLeftIcon /> : <ChevronRightIcon />}</IconButton>
      </Toolbar>

      {open && (
        <Box sx={{ flex: 1, minHeight: 0, overflow: 'hidden', px: 2, display: 'flex', flexDirection: 'column' }}>
          <Watchlist open={open} onLastTickAtChange={(d) => setLastTickAt(d)} />
        </Box>
      )}

      <Box sx={{ mt: 'auto' }}>
        <Divider />
        <List>
          {navigationItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton onClick={() => window.open(item.path, '_blank')}>
                <ListItemIcon>{item.icon}</ListItemIcon>
                {open && <ListItemText primary={item.text} />}
              </ListItemButton>
            </ListItem>
          ))}
          <ListItem disablePadding>
            <ListItemButton onClick={signOut}>
              <ListItemIcon><LogoutIcon /></ListItemIcon>
              {open && <ListItemText primary="Sign out" />}
            </ListItemButton>
          </ListItem>
        </List>
      </Box>

      {open && (
        <Box
          onMouseDown={handleResizeMouseDown}
          sx={{
            position: 'absolute',
            right: 0,
            top: 0,
            bottom: 0,
            width: 5,
            cursor: 'col-resize',
            '&:hover': { bgcolor: 'primary.main' },
          }}
        />
      )}
    </Drawer>
  );
};

export default CollapsibleDrawer;
