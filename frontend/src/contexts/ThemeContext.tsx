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

const OPENDYSLEXIC_URL = 'https://cdn.jsdelivr.net/npm/open-dyslexic@1.0.3/open-dyslexic-regular.css';

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

  // Load OpenDyslexic font when dyslexiaFont is enabled
  useEffect(() => {
    const linkId = 'opendyslexic-font';
    if (accessibility.dyslexiaFont) {
      if (!document.getElementById(linkId)) {
        const link = document.createElement('link');
        link.id = linkId;
        link.rel = 'stylesheet';
        link.href = OPENDYSLEXIC_URL;
        document.head.appendChild(link);
      }
    } else {
      const existing = document.getElementById(linkId);
      if (existing) existing.remove();
    }
  }, [accessibility.dyslexiaFont]);

  // Apply reduce-motion at CSS level
  useEffect(() => {
    if (accessibility.reduceMotion) {
      document.documentElement.style.setProperty('--reduce-motion', 'reduce');
      document.documentElement.classList.add('reduce-motion');
    } else {
      document.documentElement.style.removeProperty('--reduce-motion');
      document.documentElement.classList.remove('reduce-motion');
    }
  }, [accessibility.reduceMotion]);

  // Apply screen-reader optimized attributes
  useEffect(() => {
    if (accessibility.screenReaderOptimized) {
      document.documentElement.setAttribute('data-sr-optimized', 'true');
    } else {
      document.documentElement.removeAttribute('data-sr-optimized');
    }
  }, [accessibility.screenReaderOptimized]);

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
