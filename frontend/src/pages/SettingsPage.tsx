import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Card, CardContent, Grid, FormControl, InputLabel,
  Select, MenuItem, Switch, FormControlLabel, Divider, alpha, useTheme,
} from '@mui/material';
import { Palette, Translate, Accessibility } from '@mui/icons-material';
import i18n from '../i18n';
import { useThemeContext } from '../contexts/ThemeContext';
import { ColorBlindMode } from '../themes/accessibility';

const SettingsPage: React.FC = () => {
  const { t } = useTranslation();
  const theme = useTheme();
  const { mode, setMode, accessibility, updateAccessibility } = useThemeContext();

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} gutterBottom>{t('settings.title')}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t('app.subtitle')}
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.5 }}>
                <Box sx={{
                  p: 1, borderRadius: '10px',
                  background: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)',
                  color: '#fff', display: 'flex',
                }}>
                  <Palette fontSize="small" />
                </Box>
                <Typography variant="h6">{t('settings.theme')}</Typography>
              </Box>
              <FormControl fullWidth>
                <InputLabel>{t('settings.theme')}</InputLabel>
                <Select value={mode} label={t('settings.theme')} onChange={e => setMode(e.target.value as 'light' | 'dark')}>
                  <MenuItem value="light">{t('settings.light')}</MenuItem>
                  <MenuItem value="dark">{t('settings.dark')}</MenuItem>
                </Select>
              </FormControl>

              <Divider sx={{ my: 3 }} />

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.5 }}>
                <Box sx={{
                  p: 1, borderRadius: '10px',
                  background: 'linear-gradient(135deg, #059669 0%, #10B981 100%)',
                  color: '#fff', display: 'flex',
                }}>
                  <Translate fontSize="small" />
                </Box>
                <Typography variant="h6">{t('settings.language')}</Typography>
              </Box>
              <FormControl fullWidth>
                <InputLabel>{t('settings.language')}</InputLabel>
                <Select value={i18n.language?.substring(0, 2) || 'en'} label={t('settings.language')} onChange={e => i18n.changeLanguage(e.target.value)}>
                  <MenuItem value="en">English</MenuItem>
                  <MenuItem value="fr">Fran\u00e7ais</MenuItem>
                  <MenuItem value="es">Espa\u00f1ol</MenuItem>
                </Select>
              </FormControl>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.5 }}>
                <Box sx={{
                  p: 1, borderRadius: '10px',
                  background: 'linear-gradient(135deg, #D97706 0%, #F59E0B 100%)',
                  color: '#fff', display: 'flex',
                }}>
                  <Accessibility fontSize="small" />
                </Box>
                <Typography variant="h6">{t('settings.accessibility')}</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                <FormControlLabel control={<Switch checked={accessibility.highContrast} onChange={e => updateAccessibility({ highContrast: e.target.checked })} />} label={t('settings.highContrast')} />
                <FormControlLabel control={<Switch checked={accessibility.largeText} onChange={e => updateAccessibility({ largeText: e.target.checked })} />} label={t('settings.largeText')} />
                <FormControlLabel control={<Switch checked={accessibility.reduceMotion} onChange={e => updateAccessibility({ reduceMotion: e.target.checked })} />} label={t('settings.reduceMotion')} />
                <FormControlLabel control={<Switch checked={accessibility.enhancedFocus} onChange={e => updateAccessibility({ enhancedFocus: e.target.checked })} />} label={t('settings.focusIndicators')} />
                <FormControlLabel control={<Switch checked={accessibility.screenReaderOptimized} onChange={e => updateAccessibility({ screenReaderOptimized: e.target.checked })} />} label={t('settings.screenReader')} />
                <FormControlLabel control={<Switch checked={accessibility.dyslexiaFont} onChange={e => updateAccessibility({ dyslexiaFont: e.target.checked })} />} label={t('settings.dyslexiaFont')} />
              </Box>

              <Divider sx={{ my: 2 }} />

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
