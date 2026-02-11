import { createTheme, Theme, ThemeOptions } from '@mui/material/styles';

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
  const overrides: ThemeOptions = {};

  // --- Palette overrides ---
  const paletteOverrides: any = {};

  if (settings.highContrast) {
    paletteOverrides.contrastThreshold = 7;
    paletteOverrides.text = baseTheme.palette.mode === 'dark'
      ? { primary: '#ffffff', secondary: '#e0e0e0' }
      : { primary: '#000000', secondary: '#1a1a1a' };
    paletteOverrides.divider = baseTheme.palette.mode === 'dark' ? '#555555' : '#333333';
    paletteOverrides.background = baseTheme.palette.mode === 'dark'
      ? { default: '#000000', paper: '#121212' }
      : { default: '#ffffff', paper: '#ffffff' };
  }

  if (settings.colorBlindMode !== 'none') {
    const cbColors = colorBlindPalettes[settings.colorBlindMode];
    if (cbColors.primary) paletteOverrides.primary = { main: cbColors.primary };
    if (cbColors.secondary) paletteOverrides.secondary = { main: cbColors.secondary };
    if (cbColors.success) paletteOverrides.success = { main: cbColors.success };
    if (cbColors.error) paletteOverrides.error = { main: cbColors.error };
    if (cbColors.warning) paletteOverrides.warning = { main: cbColors.warning };
  }

  if (Object.keys(paletteOverrides).length > 0) {
    overrides.palette = paletteOverrides;
  }

  // --- Typography overrides ---
  const typographyOverrides: any = {};

  if (settings.largeText) {
    typographyOverrides.fontSize = 18;
    typographyOverrides.body1 = { fontSize: '1.125rem' };
    typographyOverrides.body2 = { fontSize: '1rem' };
    typographyOverrides.caption = { fontSize: '0.875rem' };
  }

  if (settings.dyslexiaFont) {
    typographyOverrides.fontFamily = '"OpenDyslexic", "Comic Sans MS", "Trebuchet MS", sans-serif';
  }

  if (Object.keys(typographyOverrides).length > 0) {
    overrides.typography = typographyOverrides;
  }

  // --- Component overrides ---
  const componentOverrides: any = {};

  if (settings.enhancedFocus) {
    const focusColor = settings.colorBlindMode !== 'none'
      ? colorBlindPalettes[settings.colorBlindMode].primary || baseTheme.palette.primary.main
      : baseTheme.palette.primary.main;

    componentOverrides.MuiButtonBase = {
      styleOverrides: {
        root: {
          '&:focus-visible': {
            outline: `3px solid ${focusColor}`,
            outlineOffset: '2px',
          },
        },
      },
    };
    componentOverrides.MuiButton = {
      styleOverrides: {
        root: {
          '&:focus-visible': {
            outline: `3px solid ${focusColor}`,
            outlineOffset: '2px',
          },
        },
      },
    };
    componentOverrides.MuiTextField = {
      styleOverrides: {
        root: {
          '& .Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderWidth: '3px',
          },
          '& .Mui-focused': {
            outline: `2px solid ${focusColor}`,
            outlineOffset: '1px',
          },
        },
      },
    };
    componentOverrides.MuiSelect = {
      styleOverrides: {
        root: {
          '&.Mui-focused': {
            outline: `2px solid ${focusColor}`,
            outlineOffset: '1px',
          },
        },
      },
    };
    componentOverrides.MuiSwitch = {
      styleOverrides: {
        root: {
          '& .MuiSwitch-switchBase:focus-visible': {
            outline: `3px solid ${focusColor}`,
            outlineOffset: '2px',
            borderRadius: '50%',
          },
        },
      },
    };
    componentOverrides.MuiTab = {
      styleOverrides: {
        root: {
          '&:focus-visible': {
            outline: `3px solid ${focusColor}`,
            outlineOffset: '2px',
          },
        },
      },
    };
    componentOverrides.MuiIconButton = {
      styleOverrides: {
        root: {
          '&:focus-visible': {
            outline: `3px solid ${focusColor}`,
            outlineOffset: '2px',
          },
        },
      },
    };
    componentOverrides.MuiLink = {
      styleOverrides: {
        root: {
          '&:focus-visible': {
            outline: `3px solid ${focusColor}`,
            outlineOffset: '2px',
          },
        },
      },
    };
  }

  if (settings.screenReaderOptimized) {
    componentOverrides.MuiButton = {
      ...(componentOverrides.MuiButton || {}),
      defaultProps: {
        disableRipple: true,
      },
      styleOverrides: {
        ...(componentOverrides.MuiButton?.styleOverrides || {}),
        root: {
          ...(componentOverrides.MuiButton?.styleOverrides?.root || {}),
          '&::after': {
            content: 'attr(aria-label)',
            position: 'absolute',
            width: '1px',
            height: '1px',
            overflow: 'hidden',
            clip: 'rect(0, 0, 0, 0)',
          },
        },
      },
    };
    componentOverrides.MuiIconButton = {
      ...(componentOverrides.MuiIconButton || {}),
      defaultProps: {
        disableRipple: true,
      },
    };
    componentOverrides.MuiTooltip = {
      defaultProps: {
        arrow: true,
        enterDelay: 0,
        enterTouchDelay: 0,
      },
    };
    componentOverrides.MuiCard = {
      defaultProps: {
        role: 'region',
      },
    };
    componentOverrides.MuiChip = {
      defaultProps: {
        role: 'status',
      },
    };
  }

  if (Object.keys(componentOverrides).length > 0) {
    overrides.components = componentOverrides;
  }

  // --- Transitions (reduceMotion) ---
  if (settings.reduceMotion) {
    overrides.transitions = {
      create: () => 'none',
    };
    // Also disable component animations
    componentOverrides.MuiCssBaseline = {
      ...(componentOverrides.MuiCssBaseline || {}),
      styleOverrides: {
        '*, *::before, *::after': {
          animationDuration: '0.001ms !important',
          animationIterationCount: '1 !important',
          transitionDuration: '0.001ms !important',
        },
      },
    };
    if (!overrides.components) overrides.components = {};
    overrides.components = { ...overrides.components, ...componentOverrides };
  }

  // Use MUI's 2-argument createTheme for proper deep merge
  return createTheme(baseTheme, overrides);
}
