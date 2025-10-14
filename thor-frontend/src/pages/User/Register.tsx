import React, { useState } from 'react';
import { Box, Paper, Typography, TextField, Button, FormControlLabel, Checkbox } from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import api from '../../services/api';
import './Register.css';

const Register: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [agree, setAgree] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agree) return toast.error('You must agree to the Terms & Privacy Policy');
    if (password !== confirm) return toast.error('Passwords do not match');
    setLoading(true);
    try {
      // Placeholder call; wire to backend when ready
      // await api.post('/auth/register/', { email, password });
      await new Promise((r) => setTimeout(r, 500));
      toast.success('Account created. Sign in now.');
      navigate('/auth/login');
    } catch (err: any) {
      toast.error('Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box className="register-page">
      <Paper elevation={3} className="register-card">
        <Typography variant="h4" className="register-title" gutterBottom>
          Create your account
        </Typography>
        <Typography variant="body1" color="text.secondary" gutterBottom>
          Set up your login to access paper and live accounts.
        </Typography>
        <form onSubmit={submit} className="register-form">
          <TextField label="Email" type="email" fullWidth required margin="normal" value={email} onChange={(e) => setEmail(e.target.value)} />
          <TextField label="Password" type="password" fullWidth required margin="normal" value={password} onChange={(e) => setPassword(e.target.value)} />
          <TextField label="Confirm password" type="password" fullWidth required margin="normal" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          <FormControlLabel control={<Checkbox checked={agree} onChange={(e) => setAgree(e.target.checked)} />} label="I agree to the Terms & Privacy Policy" />
          <Button type="submit" variant="contained" color="primary" disabled={loading} fullWidth sx={{ mt: 2 }}>
            {loading ? 'Creating…' : 'Create account'}
          </Button>
          <Typography variant="caption" display="block" sx={{ mt: 2 }}>
            You’ll start with a $100,000 paper account. You can connect a live account later.
          </Typography>
          <Typography variant="body2" sx={{ mt: 2 }}>
            Already have an account? <Link to="/auth/login">Sign in</Link>
          </Typography>
        </form>
      </Paper>
    </Box>
  );
};

export default Register;
