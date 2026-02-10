import { createTheme } from '@mui/material/styles';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#818CF8', light: '#C7D2FE', dark: '#6366F1', contrastText: '#ffffff' },
    secondary: { main: '#A78BFA', light: '#DDD6FE', dark: '#8B5CF6', contrastText: '#ffffff' },
    background: { default: '#0F172A', paper: '#1E293B' },
    success: { main: '#34D399', light: '#064E3B', dark: '#10B981' },
    warning: { main: '#FBBF24', light: '#78350F', dark: '#F59E0B' },
    error: { main: '#F87171', light: '#7F1D1D', dark: '#EF4444' },
    info: { main: '#60A5FA', light: '#1E3A5F', dark: '#3B82F6' },
    text: { primary: '#F1F5F9', secondary: '#94A3B8' },
    divider: '#334155',
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 700, letterSpacing: '-0.02em' },
    h5: { fontWeight: 600, letterSpacing: '-0.01em' },
    h6: { fontWeight: 600 },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 10,
          padding: '8px 20px',
          boxShadow: 'none',
          '&:hover': { boxShadow: 'none' },
        },
        contained: {
          background: 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
          '&:hover': {
            background: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)',
          },
        },
        outlined: {
          borderWidth: '1.5px',
          borderColor: '#475569',
          '&:hover': { borderWidth: '1.5px', borderColor: '#818CF8' },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
          border: '1px solid #334155',
          borderRadius: 16,
          transition: 'box-shadow 0.2s ease, transform 0.2s ease',
          '&:hover': {
            boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
          },
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: 'none',
          background: 'linear-gradient(180deg, #0F172A 0%, #1E1B4B 100%)',
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-head': {
            backgroundColor: '#1E293B',
            color: '#94A3B8',
            fontWeight: 600,
            fontSize: '0.8125rem',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            borderBottom: '2px solid #334155',
          },
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover': {
            backgroundColor: '#1E293B !important',
          },
          '&:last-child td': {
            borderBottom: 0,
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid #334155',
          padding: '14px 16px',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
          borderRadius: 8,
        },
        colorSuccess: {
          backgroundColor: '#064E3B',
          color: '#34D399',
        },
        colorWarning: {
          backgroundColor: '#78350F',
          color: '#FBBF24',
        },
        colorError: {
          backgroundColor: '#7F1D1D',
          color: '#F87171',
        },
        colorInfo: {
          backgroundColor: '#1E3A5F',
          color: '#60A5FA',
        },
        colorPrimary: {
          backgroundColor: '#312E81',
          color: '#A5B4FC',
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 16,
          boxShadow: '0 25px 50px rgba(0,0,0,0.3)',
          border: '1px solid #334155',
        },
      },
    },
    MuiDialogTitle: {
      styleOverrides: {
        root: {
          fontWeight: 600,
          fontSize: '1.25rem',
          padding: '20px 24px 12px',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 10,
            '&:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: '#6366F1',
            },
            '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
              borderColor: '#818CF8',
              borderWidth: '2px',
            },
          },
        },
      },
    },
    MuiAccordion: {
      styleOverrides: {
        root: {
          borderRadius: '12px !important',
          border: '1px solid #334155',
          boxShadow: 'none',
          '&:before': { display: 'none' },
          '&.Mui-expanded': {
            margin: '0 0 8px 0',
          },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          '&.Mui-selected': {
            backgroundColor: 'rgba(129,140,248,0.15)',
            '&:hover': {
              backgroundColor: 'rgba(129,140,248,0.2)',
            },
          },
          '&:hover': {
            backgroundColor: 'rgba(255,255,255,0.05)',
          },
        },
      },
    },
    MuiSwitch: {
      styleOverrides: {
        root: {
          '& .MuiSwitch-switchBase.Mui-checked': {
            color: '#818CF8',
          },
          '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
            backgroundColor: '#818CF8',
          },
        },
      },
    },
  },
});

export default darkTheme;
