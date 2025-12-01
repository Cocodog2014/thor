import React from 'react';
import { Container, Box, Typography } from '@mui/material';
import FutureRTD from '../FutureRTD/FutureRTD';
import './FutureHome.css';

// Simple wrapper home for Futures area. Shows heading + embeds RTD grid.
const FutureHome: React.FC = () => {
  return (
    <Box className="future-home-root" sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <Box className="future-home-header" sx={{ px: 3, py: 2, borderBottom: '1px solid rgba(255,255,255,0.15)' }}>
        <Typography variant="h5" className="future-home-title">Futures Dashboard</Typography>
        <Typography variant="body2" className="future-home-subtitle" color="text.secondary">
          Real Time Data (RTD) feed cards (11 core contracts + composite total)
        </Typography>
      </Box>
      <Box sx={{ flex: 1, overflow: 'auto' }} className="future-home-scroll">
        <Container maxWidth={false} sx={{ pt: 3, pb: 6 }}>
          <FutureRTD />
        </Container>
      </Box>
    </Box>
  );
};

export default FutureHome;
