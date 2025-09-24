import React from 'react';
import {
  Paper,
  Typography,
  Box,
} from '@mui/material';
import {
  TrendingUp as PowerIcon,
} from '@mui/icons-material';

const Dashboard: React.FC = () => {
  return (
    <Box>
      <Typography 
        variant="h3" 
        component="h1" 
        gutterBottom 
        sx={{ 
          fontFamily: '"Cinzel", serif',
          textAlign: 'center',
          mb: 4,
          background: 'linear-gradient(45deg, #1976d2, #42a5f5)',
          backgroundClip: 'text',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}
      >
        🌩️ Realm of Asgard Dashboard 🌩️
      </Typography>

      <Box 
        sx={{ 
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
          gap: 3
        }}
      >
        <Paper sx={{ p: 3, background: 'linear-gradient(135deg, #1976d220, #1976d210)' }}>
          <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <PowerIcon /> System Statistics
          </Typography>
          <Typography color="textSecondary">Heroes/Quests/Artifacts have been removed. No stats endpoint is currently wired.</Typography>
        </Paper>
      </Box>

      <Paper sx={{ p: 4, mt: 4, textAlign: 'center', background: 'linear-gradient(45deg, #1a1f2e, #0a0e13)' }}>
        <Typography variant="h4" gutterBottom sx={{ fontFamily: '"Cinzel", serif' }}>
          Welcome to the Realm of Thor! ⚡
        </Typography>
        <Typography variant="body1" sx={{ maxWidth: 600, mx: 'auto', color: 'text.secondary' }}>
          Explore world market times and use the Global Markets module.
        </Typography>
      </Paper>
    </Box>
  );
};

export default Dashboard;