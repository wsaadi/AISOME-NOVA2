import React, { createContext, useContext, useState, useMemo, useEffect } from 'react';
import { ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import lightTheme from '../themes/light';
import darkTheme from '../themes/dark';
import {
  AccessibilitySettings,
  defaultAccessibility,
  applyAccessibility,
} from '../themes/accessibility';

type ThemeMode = 'light' | 'dark';

interface ThemeContextType {
  mode: ThemeMode;
  toggleTheme: () => void;
  setMode: (mode: ThemeMode) => void;
  accessibility: AccessibilitySettings;
  updateAccessibility: (settings: Partial<AccessibilitySettings>) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setMode] = useState<ThemeMode>(
    () => (localStorage.getItem('theme') as ThemeMode) || 'light'
  );
  const [accessibility, setAccessibility] = useState<AccessibilitySettings>(() => {
    const stored = localStorage.getItem('accessibility');
    return stored ? JSON.parse(stored) : defaultAccessibility;
  });

  useEffect(() => { localStorage.setItem('theme', mode); }, [mode]);
  useEffect(() => { localStorage.setItem('accessibility', JSON.stringify(accessibility)); }, [accessibility]);

  const toggleTheme = () => setMode((prev) => (prev === 'light' ? 'dark' : 'light'));

  const updateAccessibility = (settings: Partial<AccessibilitySettings>) => {
    setAccessibility((prev) => ({ ...prev, ...settings }));
  };

  const theme = useMemo(() => {
    const base = mode === 'light' ? lightTheme : darkTheme;
    return applyAccessibility(base, accessibility);
  }, [mode, accessibility]);

  return (
    <ThemeContext.Provider value={{ mode, toggleTheme, setMode, accessibility, updateAccessibility }}>
      <MuiThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </MuiThemeProvider>
    </ThemeContext.Provider>
  );
};

export const useThemeContext = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useThemeContext must be used within ThemeProvider');
  return context;
};
