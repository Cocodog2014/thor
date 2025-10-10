import { createTheme } from '@mui/material/styles';

// Unified theme that matches global.css black canvas
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#1976d2' }, // Thor blue (matches global.css --thor-blue-primary)
    secondary: { main: '#4caf50' }, // Thor green (matches global.css --thor-green)
    background: {
      default: '#000000', // Pure black to match global.css
      paper: 'rgba(255, 255, 255, 0.1)', // Semi-transparent white (matches global.css)
    },
    text: {
      primary: '#ffffff', // White text on black canvas
      secondary: 'rgba(255, 255, 255, 0.7)',
    },
  },
  typography: {
    h1: { fontFamily: '"Cinzel", serif', color: '#ffffff' }, // Thor title font
    h2: { fontFamily: '"Cinzel", serif', color: '#ffffff' },
    h3: { fontFamily: '"Cinzel", serif', color: '#ffffff' },
    h4: { fontFamily: '"Cinzel", serif', color: '#ffffff' },
    body1: { fontFamily: '"Inter", sans-serif', color: '#ffffff' }, // Matches global.css
    body2: { fontFamily: '"Inter", sans-serif', color: '#ffffff' },
  },
  components: {
    // Override MUI components to work with black canvas
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(255, 255, 255, 0.1)', // Semi-transparent overlay
          color: '#ffffff',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: 'linear-gradient(45deg, #1976d2 30%, #42a5f5 90%)', // Matches GlobalHeader.css
        },
      },
    },
  },
});

export default theme;
