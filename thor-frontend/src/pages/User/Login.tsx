import React, { useState } from 'react';
import { Box, Paper, Typography, TextField, Button } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import api from '../../services/api';
import './Login.css';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const location = useLocation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      // Call Django JWT login endpoint
      // Note: Backend expects 'email' field (CustomUser.USERNAME_FIELD = 'email')
      const { data } = await api.post('/api/users/login/', { 
        email: email,  // CustomUser uses email as USERNAME_FIELD
        password 
      });
      
      // Store JWT tokens
      localStorage.setItem('thor_access_token', data.access);
      localStorage.setItem('thor_refresh_token', data.refresh);
      
      toast.success('Logged in successfully!');
      const params = new URLSearchParams(location.search);
      const next = params.get('next') || '/app/user';
      navigate(next);
    } catch (err: any) {
      console.error('Login error:', err);
      const message = err.response?.data?.non_field_errors?.[0] || err.response?.data?.detail || 'Invalid credentials';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box className="login-page" sx={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-start', p: 3 }}>
      <Paper elevation={6} className="login-card">
        {/* Thor Branding */}
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Typography variant="h3" sx={{ fontSize: '3.75rem', mb: 1 }} className="lightning-animated thor-branding-animated">
            ⚡🔨⚡
          </Typography>
          <Typography variant="h4" className="login-title" sx={{ fontWeight: 600, letterSpacing: 1 }}>
            THOR'S WAR ROOM
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Sign in
          </Typography>
        </Box>

        <form onSubmit={handleSubmit} className="login-form">
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            fullWidth
            required
            margin="normal"
            variant="filled"
            sx={{ mb: 2 }}
          />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            fullWidth
            required
            margin="normal"
            variant="filled"
            sx={{ mb: 3 }}
          />
          <Button 
            type="submit" 
            variant="contained" 
            disabled={loading} 
            fullWidth 
            sx={{ 
              mt: 1,
              py: 1.5,
              background: 'linear-gradient(45deg, #1976d2 30%, #42a5f5 90%)',
              fontSize: '1rem',
              fontWeight: 600,
              '&:hover': {
                background: 'linear-gradient(45deg, #1565c0 30%, #1976d2 90%)',
              }
            }}
          >
            {loading ? 'Logging in…' : 'LOGIN'}
          </Button>
          <Typography variant="body2" sx={{ mt: 3, textAlign: 'center' }}>
            Don't have an account? <a href="/auth/register" style={{ color: '#42a5f5', fontWeight: 500 }}>Create one</a>
          </Typography>
        </form>
      </Paper>
    </Box>
  );
};

export default Login;
