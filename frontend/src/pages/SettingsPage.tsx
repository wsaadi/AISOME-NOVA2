import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Card, CardContent, Grid, FormControl, InputLabel,
  Select, MenuItem, Switch, FormControlLabel, Divider, alpha, useTheme,
  Tabs, Tab, Button, CircularProgress, Alert,
} from '@mui/material';
import {
  Palette, Translate, Accessibility, People, Security, Settings as SettingsIcon,
  Shield, CloudUpload, Delete, Image, Build, SmartToy,
} from '@mui/icons-material';
import i18n from '../i18n';
import { useThemeContext } from '../contexts/ThemeContext';
import { ColorBlindMode } from '../themes/accessibility';
import UsersPage from './UsersPage';
import RolesPage from './RolesPage';
import LLMConfigPage from './LLMConfigPage';
import ModerationPage from './ModerationPage';
import ToolsConfigPage from './ToolsConfigPage';
import AgentLLMConfigPage from './AgentLLMConfigPage';
import api from '../services/api';
import { useSnackbar } from 'notistack';

/* ── General Tab ── */
const GeneralTab: React.FC = () => {
  const { t } = useTranslation();
  const { mode, setMode, accessibility, updateAccessibility } = useThemeContext();

  return (
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
                <MenuItem value="fr">Français</MenuItem>
                <MenuItem value="es">Español</MenuItem>
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
  );
};

/* ── Logo Tab ── */
const LogoTab: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const fetchLogo = useCallback(async () => {
    try {
      const res = await api.get('/api/system/logo', { responseType: 'blob' });
      setLogoUrl(URL.createObjectURL(res.data));
    } catch {
      setLogoUrl(null);
    }
  }, []);

  useEffect(() => { fetchLogo(); }, [fetchLogo]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      await api.post('/api/system/logo', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      enqueueSnackbar(t('common.success'), { variant: 'success' });
      fetchLogo();
    } catch (err: any) {
      enqueueSnackbar(err.response?.data?.detail || t('common.error'), { variant: 'error' });
    }
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDelete = async () => {
    try {
      await api.delete('/api/system/logo');
      setLogoUrl(null);
      enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch {
      enqueueSnackbar(t('common.error'), { variant: 'error' });
    }
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.5 }}>
              <Box sx={{
                p: 1, borderRadius: '10px',
                background: 'linear-gradient(135deg, #7C3AED 0%, #EC4899 100%)',
                color: '#fff', display: 'flex',
              }}>
                <Image fontSize="small" />
              </Box>
              <Typography variant="h6">{t('settings.platformLogo')}</Typography>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              {t('settings.logoDescription')}
            </Typography>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleUpload}
              style={{ display: 'none' }}
              accept=".png,.jpg,.jpeg,.svg,.webp"
            />
            <Box sx={{ display: 'flex', gap: 1.5 }}>
              <Button
                variant="contained"
                startIcon={uploading ? <CircularProgress size={18} color="inherit" /> : <CloudUpload />}
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                sx={{ borderRadius: 2 }}
              >
                {t('settings.uploadLogo')}
              </Button>
              {logoUrl && (
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<Delete />}
                  onClick={handleDelete}
                  sx={{ borderRadius: 2 }}
                >
                  {t('settings.deleteLogo')}
                </Button>
              )}
            </Box>
            <Alert severity="info" sx={{ mt: 2, borderRadius: 2 }}>
              PNG, JPG, SVG, WebP
            </Alert>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent sx={{ p: 3, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 250 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{t('settings.logoPreview')}</Typography>
            {logoUrl ? (
              <Box
                component="img"
                src={logoUrl}
                alt="Platform logo"
                sx={{
                  maxWidth: '100%',
                  maxHeight: 180,
                  objectFit: 'contain',
                  borderRadius: 2,
                  border: `1px solid ${theme.palette.divider}`,
                  p: 2,
                }}
              />
            ) : (
              <Box sx={{
                width: 140, height: 140,
                borderRadius: 3,
                border: `2px dashed ${alpha(theme.palette.text.secondary, 0.3)}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexDirection: 'column', gap: 1,
              }}>
                <Image sx={{ fontSize: 48, color: alpha(theme.palette.text.secondary, 0.3) }} />
                <Typography variant="caption" color="text.secondary">{t('settings.noLogo')}</Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

/* ── Main Settings Page ── */
const SettingsPage: React.FC = () => {
  const { t } = useTranslation();
  const [tab, setTab] = useState(0);

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} gutterBottom>{t('settings.title')}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{t('app.subtitle')}</Typography>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            '& .MuiTab-root': { textTransform: 'none', fontWeight: 600, fontSize: '0.9rem', minHeight: 48 },
            '& .MuiTabs-indicator': { height: 3, borderRadius: '3px 3px 0 0' },
          }}
        >
          <Tab icon={<SettingsIcon fontSize="small" />} iconPosition="start" label={t('settings.general')} />
          <Tab icon={<People fontSize="small" />} iconPosition="start" label={t('users.title')} />
          <Tab icon={<Security fontSize="small" />} iconPosition="start" label={t('roles.title')} />
          <Tab icon={<SettingsIcon fontSize="small" />} iconPosition="start" label={t('llm.title')} />
          <Tab icon={<Shield fontSize="small" />} iconPosition="start" label={t('moderation.title')} />
          <Tab icon={<Build fontSize="small" />} iconPosition="start" label={t('tools.title')} />
          <Tab icon={<SmartToy fontSize="small" />} iconPosition="start" label={t('agentLlmConfig.title')} />
          <Tab icon={<Image fontSize="small" />} iconPosition="start" label={t('settings.logo')} />
        </Tabs>
      </Box>

      {tab === 0 && <GeneralTab />}
      {tab === 1 && <UsersPage />}
      {tab === 2 && <RolesPage />}
      {tab === 3 && <LLMConfigPage />}
      {tab === 4 && <ModerationPage />}
      {tab === 5 && <ToolsConfigPage />}
      {tab === 6 && <AgentLLMConfigPage />}
      {tab === 7 && <LogoTab />}
    </Box>
  );
};

export default SettingsPage;
