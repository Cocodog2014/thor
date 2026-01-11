import React, { useEffect, useState } from 'react';
import { Box, Paper, Typography, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';

type UserProfile = {
  is_approved?: boolean;
  email?: string;
};

const PendingApproval: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuth();
  const [email, setEmail] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);
  const [approved, setApproved] = useState(false);

  useEffect(() => {
    let active = true;

    const run = async () => {
      if (!isAuthenticated) {
        navigate('/auth/login', { replace: true });
        return;
      }

      try {
        setChecking(true);
        const { data } = await api.get<UserProfile>('/users/profile/');
        if (!active) return;

        setEmail(typeof data?.email === 'string' ? data.email : null);
        const isApproved = Boolean(data?.is_approved);
        setApproved(isApproved);

        if (isApproved) {
          navigate('/app/home', { replace: true });
        }
      } catch {
        if (!active) return;
        // If profile fails, force re-login.
        logout();
        navigate('/auth/login', { replace: true });
      } finally {
        if (active) setChecking(false);
      }
    };

    run();

    return () => {
      active = false;
    };
  }, [isAuthenticated, navigate, logout]);

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-start', p: 3 }}>
      <Paper elevation={6} sx={{ maxWidth: 520, width: '100%', p: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Waiting for approval
        </Typography>
        <Typography variant="body1" sx={{ mb: 2 }}>
          Your account{email ? ` (${email})` : ''} has been created, but an admin must approve it before you can use the app.
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {checking
            ? 'Checking approval status…'
            : approved
              ? 'Approved — redirecting…'
              : 'Once approved, refresh this page or sign in again.'}
        </Typography>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="contained" onClick={() => window.location.reload()} disabled={checking}>
            Refresh status
          </Button>
          <Button variant="outlined" onClick={() => { logout(); navigate('/auth/login'); }}>
            Sign out
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};

export default PendingApproval;
