import React, { useState } from 'react';
import { Box, Paper, Typography, TextField, Button, FormControlLabel, Checkbox } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
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
    <Box className="register-page" sx={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-start', p: 3 }}>
      <Paper elevation={6} className="register-card">
        {/* Thor Branding */}
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Typography variant="h3" sx={{ fontSize: '3.75rem', mb: 1 }} className="lightning-animated thor-branding-animated">
            ⚡🔨⚡
          </Typography>
          <Typography variant="h4" className="register-title" sx={{ fontWeight: 600, letterSpacing: 1 }}>
            THOR'S WAR ROOM
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Create your account
          </Typography>
        </Box>

        <form onSubmit={submit} className="register-form">
          <TextField 
            label="Email" 
            type="email" 
            fullWidth 
            required 
            margin="normal" 
            variant="filled"
            value={email} 
            onChange={(e) => setEmail(e.target.value)} 
            sx={{ mb: 2 }}
          />
          <TextField 
            label="Password" 
            type="password" 
            fullWidth 
            required 
            margin="normal" 
            variant="filled"
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
            sx={{ mb: 2 }}
          />
          <TextField 
            label="Confirm password" 
            type="password" 
            fullWidth 
            required 
            margin="normal" 
            variant="filled"
            value={confirm} 
            onChange={(e) => setConfirm(e.target.value)} 
            sx={{ mb: 2 }}
          />
          <FormControlLabel 
            control={<Checkbox checked={agree} onChange={(e) => setAgree(e.target.checked)} />} 
            label="I agree to the Terms & Privacy Policy" 
            sx={{ mt: 1, mb: 2 }}
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
            {loading ? 'Creating…' : 'CREATE ACCOUNT'}
          </Button>
          <Typography variant="caption" display="block" sx={{ mt: 2, textAlign: 'center', color: 'rgba(255,255,255,0.7)' }}>
            You'll start with a $100,000 paper account. You can connect a live account later.
          </Typography>
          <Typography variant="body2" sx={{ mt: 2, textAlign: 'center' }}>
            Already have an account? <a href="/auth/login" style={{ color: '#42a5f5', fontWeight: 500 }}>Sign in</a>
          </Typography>
        </form>
      </Paper>
    </Box>
  );
};

export default Register;
