import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Card, CardContent, Grid, FormControl, InputLabel,
  Select, MenuItem, Switch, FormControlLabel, Divider,
} from '@mui/material';
import i18n from '../i18n';
import { useThemeContext } from '../contexts/ThemeContext';
import { ColorBlindMode } from '../themes/accessibility';

const SettingsPage: React.FC = () => {
  const { t } = useTranslation();
  const { mode, setMode, accessibility, updateAccessibility } = useThemeContext();

  return (
    <Box>
      <Typography variant="h4" fontWeight={600} gutterBottom>{t('settings.title')}</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>{t('settings.theme')}</Typography>
              <FormControl fullWidth>
                <InputLabel>{t('settings.theme')}</InputLabel>
                <Select value={mode} label={t('settings.theme')} onChange={e => setMode(e.target.value as 'light' | 'dark')}>
                  <MenuItem value="light">{t('settings.light')}</MenuItem>
                  <MenuItem value="dark">{t('settings.dark')}</MenuItem>
                </Select>
              </FormControl>
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6" gutterBottom>{t('settings.language')}</Typography>
              <FormControl fullWidth>
                <InputLabel>{t('settings.language')}</InputLabel>
                <Select value={i18n.language?.substring(0, 2) || 'en'} label={t('settings.language')} onChange={e => i18n.changeLanguage(e.target.value)}>
                  <MenuItem value="en">English</MenuItem>
                  <MenuItem value="fr">Français</MenuItem>
                  <MenuItem value="es">Español</MenuItem>
                </Select>
              </FormControl>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>{t('settings.accessibility')}</Typography>
              <FormControlLabel control={<Switch checked={accessibility.highContrast} onChange={e => updateAccessibility({ highContrast: e.target.checked })} />} label={t('settings.highContrast')} sx={{ display: 'block', mb: 1 }} />
              <FormControlLabel control={<Switch checked={accessibility.largeText} onChange={e => updateAccessibility({ largeText: e.target.checked })} />} label={t('settings.largeText')} sx={{ display: 'block', mb: 1 }} />
              <FormControlLabel control={<Switch checked={accessibility.reduceMotion} onChange={e => updateAccessibility({ reduceMotion: e.target.checked })} />} label={t('settings.reduceMotion')} sx={{ display: 'block', mb: 1 }} />
              <FormControlLabel control={<Switch checked={accessibility.enhancedFocus} onChange={e => updateAccessibility({ enhancedFocus: e.target.checked })} />} label={t('settings.focusIndicators')} sx={{ display: 'block', mb: 1 }} />
              <FormControlLabel control={<Switch checked={accessibility.screenReaderOptimized} onChange={e => updateAccessibility({ screenReaderOptimized: e.target.checked })} />} label={t('settings.screenReader')} sx={{ display: 'block', mb: 1 }} />
              <FormControlLabel control={<Switch checked={accessibility.dyslexiaFont} onChange={e => updateAccessibility({ dyslexiaFont: e.target.checked })} />} label={t('settings.dyslexiaFont')} sx={{ display: 'block', mb: 2 }} />
              <FormControl fullWidth>
                <InputLabel>{t('settings.colorBlindMode')}</InputLabel>
                <Select value={accessibility.colorBlindMode} label={t('settings.colorBlindMode')} onChange={e => updateAccessibility({ colorBlindMode: e.target.value as ColorBlindMode })}>
                  <MenuItem value="none">{t('settings.none')}</MenuItem>
                  <MenuItem value="protanopia">{t('settings.protanopia')}</MenuItem>
                  <MenuItem value="deuteranopia">{t('settings.deuteranopia')}</MenuItem>
                  <MenuItem value="tritanopia">{t('settings.tritanopia')}</MenuItem>
                </Select>
              </FormControl>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SettingsPage;
