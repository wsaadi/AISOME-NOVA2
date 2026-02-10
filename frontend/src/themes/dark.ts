import { createTheme } from '@mui/material/styles';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#90caf9', light: '#e3f2fd', dark: '#42a5f5' },
    secondary: { main: '#ce93d8', light: '#f3e5f5', dark: '#ab47bc' },
    background: { default: '#121212', paper: '#1e1e1e' },
    success: { main: '#66bb6a' },
    warning: { main: '#ffa726' },
    error: { main: '#f44336' },
    info: { main: '#29b6f6' },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 600 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
  },
  shape: { borderRadius: 8 },
  components: {
    MuiButton: { styleOverrides: { root: { textTransform: 'none', fontWeight: 500 } } },
    MuiCard: { styleOverrides: { root: { boxShadow: '0 1px 3px rgba(0,0,0,0.3)' } } },
    MuiDrawer: { styleOverrides: { paper: { borderRight: 'none' } } },
  },
});

export default darkTheme;
