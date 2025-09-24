import { createTheme } from '@mui/material/styles';

// Centralized MUI theme for the app
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#1976d2' }, // Thor blue
    secondary: { main: '#f50057' }, // Lightning red
    background: {
      default: '#0a0e13',
      paper: '#1a1f2e',
    },
  },
  typography: {
    h1: { fontFamily: '"Cinzel", serif' },
    h2: { fontFamily: '"Cinzel", serif' },
    h3: { fontFamily: '"Cinzel", serif' },
    h4: { fontFamily: '"Cinzel", serif' },
  },
});

export default theme;
