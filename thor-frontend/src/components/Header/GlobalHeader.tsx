import React, { useEffect, useState } from 'react';
import { AppBar, Toolbar, Typography, Box, CssBaseline } from '@mui/material';
import CollapsibleDrawer, { DEFAULT_WIDTH_OPEN, DEFAULT_WIDTH_CLOSED } from '../Drawer/CollapsibleDrawer';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';

type UserProfile = {
  id?: number | null;
  first_name?: string | null;
  last_name?: string | null;
  email?: string | null;
};

type DrawerPrefs = {
  open?: boolean;
  width?: number;
};

const drawerStorageKeyForUser = (userId: number) => `thor:ui:drawer:${userId}`;

interface LayoutProps {
  children: React.ReactNode;
}

const GlobalHeader: React.FC<LayoutProps> = ({ children }) => {
  const [open, setOpen] = useState(false);
  const [commanderDisplay, setCommanderDisplay] = useState<string | null>(null);
  const [drawerStorageKey, setDrawerStorageKey] = useState<string | undefined>(undefined);
  const { token } = useAuth();

  useEffect(() => {
    let active = true;

    const fetchProfile = async () => {
      try {
        const { data } = await api.get<UserProfile>('/users/profile/');
        if (!active) {
          return;
        }

        const userId = typeof data?.id === 'number' ? data.id : undefined;
        if (userId !== undefined) {
          const key = drawerStorageKeyForUser(userId);
          setDrawerStorageKey(key);
          try {
            const raw = window.localStorage.getItem(key);
            if (raw) {
              const prefs = JSON.parse(raw) as DrawerPrefs;
              if (typeof prefs?.open === 'boolean') {
                setOpen(prefs.open);
              }
            }
          } catch {
            // ignore storage issues
          }
        } else {
          setDrawerStorageKey(undefined);
        }

        const last = data?.last_name?.trim();
        const first = data?.first_name?.trim();
        const email = data?.email?.trim();

        if (last) {
          setCommanderDisplay(`Commander ${last}`);
        } else if (first) {
          setCommanderDisplay(`Commander ${first}`);
        } else if (email) {
          setCommanderDisplay(email);
        } else {
          setCommanderDisplay(null);
        }
      } catch (error) {
        if (active) {
          console.error('GlobalHeader: failed to load commander identity', error);
          setCommanderDisplay(null);
        }
      }
    };

    if (token) {
      fetchProfile();
    } else {
      setCommanderDisplay(null);
      setDrawerStorageKey(undefined);
      setOpen(false);
    }

    return () => {
      active = false;
    };
  }, [token]);

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
            noWrap={false}
            component="div" 
            className="header-title"
          >
            <span className="header-title__primary">⚡🔨⚡ THOR'S WAR ROOM ⚡🔨⚡</span>
          </Typography>

          <Box className="header-identity">
            {commanderDisplay && (
              <>
                <Typography component="span" className="header-identity__label">
                  Commander in charge
                </Typography>
                <Typography component="span" className="header-identity__text">
                  {commanderDisplay}
                </Typography>
              </>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      {/* Sidebar */}
  <CollapsibleDrawer 
    open={open} 
    onToggle={toggleDrawer} 
    widthOpen={DEFAULT_WIDTH_OPEN} 
    widthClosed={DEFAULT_WIDTH_CLOSED}
    storageKey={drawerStorageKey}
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
