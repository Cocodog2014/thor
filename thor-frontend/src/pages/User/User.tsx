import React from 'react';
import { Box, Typography, Paper, Button, Divider } from '@mui/material';

const User: React.FC = () => {
  return (
    <Box className="user-page" sx={{ p: 2 }}>
      <Typography variant="h4" className="user-title" gutterBottom>
        User Settings
      </Typography>

      {/* Two-column responsive layout without Grid (simple flex) */}
      <Box className="user-sections" sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        {/* Profile */}
        <Box className="user-col">
          <Paper className="user-section" elevation={3}>
            <Typography variant="h6" gutterBottom>
              Profile
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <Box className="user-section-content">
              {/* Placeholder fields; will connect to API later */}
              <Box className="user-field">
                <span className="label">Name</span>
                <span className="value">—</span>
              </Box>
              <Box className="user-field">
                <span className="label">Email</span>
                <span className="value">—</span>
              </Box>
              <Box className="user-field">
                <span className="label">Role</span>
                <span className="value">—</span>
              </Box>
              <Box className="user-actions">
                <Button variant="contained" color="primary" disabled>
                  Edit Profile
                </Button>
              </Box>
            </Box>
          </Paper>
        </Box>

        {/* Accounts */}
        <Box className="user-col">
          <Paper className="user-section" elevation={3}>
            <Typography variant="h6" gutterBottom>
              Accounts
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <Box className="user-section-content">
              <Typography variant="body2" color="text.secondary">
                No accounts loaded. API wiring coming next.
              </Typography>
              <Box className="user-actions">
                <Button variant="outlined" color="primary" disabled>
                  Create Paper Account
                </Button>
              </Box>
            </Box>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
};

export default User;
