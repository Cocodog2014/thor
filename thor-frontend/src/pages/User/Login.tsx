import React, { useState } from 'react';
import { Box, Paper, Typography, TextField, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import api from '../../services/api';
import './Login.css';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      // Placeholder: call backend when endpoint is ready
      // const { data } = await api.post('/auth/login/', { email, password });
      // localStorage.setItem('thor_token', data.token);
      // toast.success('Logged in');
      // navigate('/user');

      // Temporary no-backend simulation
      await new Promise((r) => setTimeout(r, 500));
      localStorage.setItem('thor_token', 'dev-token');
      toast.success('Logged in (dev)');
      navigate('/user');
    } catch (err: any) {
      toast.error('Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box className="login-page" sx={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-start', p: 3 }}>
      <Paper elevation={3} className="login-card">
        <Typography variant="h4" className="login-title" gutterBottom>
          Login
        </Typography>
        <form onSubmit={handleSubmit} className="login-form">
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            fullWidth
            required
            margin="normal"
          />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            fullWidth
            required
            margin="normal"
          />
          <Button type="submit" variant="contained" color="primary" disabled={loading} fullWidth sx={{ mt: 2 }}>
            {loading ? 'Logging in…' : 'Login'}
          </Button>
        </form>
      </Paper>
    </Box>
  );
};

export default Login;
