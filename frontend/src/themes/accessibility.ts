import { createTheme, Theme } from '@mui/material/styles';

export type ColorBlindMode = 'none' | 'protanopia' | 'deuteranopia' | 'tritanopia';

export interface AccessibilitySettings {
  highContrast: boolean;
  largeText: boolean;
  reduceMotion: boolean;
  colorBlindMode: ColorBlindMode;
  screenReaderOptimized: boolean;
  enhancedFocus: boolean;
  dyslexiaFont: boolean;
}

export const defaultAccessibility: AccessibilitySettings = {
  highContrast: false,
  largeText: false,
  reduceMotion: false,
  colorBlindMode: 'none',
  screenReaderOptimized: false,
  enhancedFocus: false,
  dyslexiaFont: false,
};

const colorBlindPalettes: Record<ColorBlindMode, Record<string, string>> = {
  none: {},
  protanopia: { primary: '#0077BB', secondary: '#EE7733', success: '#009988', error: '#CC3311', warning: '#EE3377' },
  deuteranopia: { primary: '#0077BB', secondary: '#EE7733', success: '#009988', error: '#CC3311', warning: '#EE3377' },
  tritanopia: { primary: '#EE7733', secondary: '#0077BB', success: '#009988', error: '#CC3311', warning: '#33BBEE' },
};

export function applyAccessibility(baseTheme: Theme, settings: AccessibilitySettings): Theme {
  let theme = baseTheme;
  const overrides: any = { palette: {}, typography: {}, components: {} };

  if (settings.highContrast) {
    overrides.palette = {
      ...overrides.palette,
      contrastThreshold: 7,
      text: baseTheme.palette.mode === 'dark'
        ? { primary: '#ffffff', secondary: '#e0e0e0' }
        : { primary: '#000000', secondary: '#333333' },
    };
  }

  if (settings.colorBlindMode !== 'none') {
    const cbColors = colorBlindPalettes[settings.colorBlindMode];
    overrides.palette = {
      ...overrides.palette,
      primary: { main: cbColors.primary || baseTheme.palette.primary.main },
      secondary: { main: cbColors.secondary || baseTheme.palette.secondary.main },
      success: { main: cbColors.success || baseTheme.palette.success.main },
      error: { main: cbColors.error || baseTheme.palette.error.main },
      warning: { main: cbColors.warning || baseTheme.palette.warning.main },
    };
  }

  const baseFontSize = settings.largeText ? 18 : 14;
  const fontFamily = settings.dyslexiaFont
    ? '"OpenDyslexic", "Comic Sans MS", "Inter", sans-serif'
    : baseTheme.typography.fontFamily;

  overrides.typography = {
    ...overrides.typography,
    fontSize: baseFontSize,
    fontFamily,
  };

  if (settings.enhancedFocus) {
    overrides.components = {
      ...overrides.components,
      MuiButtonBase: {
        styleOverrides: {
          root: {
            '&:focus-visible': {
              outline: `3px solid ${baseTheme.palette.primary.main}`,
              outlineOffset: '2px',
            },
          },
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            '& .Mui-focused': {
              outline: `2px solid ${baseTheme.palette.primary.main}`,
              outlineOffset: '1px',
            },
          },
        },
      },
    };
  }

  return createTheme({
    ...baseTheme,
    palette: { ...baseTheme.palette, ...overrides.palette },
    typography: { ...baseTheme.typography, ...overrides.typography },
    components: { ...baseTheme.components, ...overrides.components },
    transitions: settings.reduceMotion ? { create: () => 'none' } : baseTheme.transitions,
  });
}
