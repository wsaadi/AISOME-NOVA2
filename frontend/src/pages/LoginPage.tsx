import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Box, Card, CardContent, TextField, Button, Typography, Alert,
  Container, Select, MenuItem, FormControl, InputLabel, alpha,
} from '@mui/material';
import { SmartToy } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import i18n from '../i18n';

const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login({ email, password });
      navigate('/dashboard');
    } catch {
      setError(t('auth.loginError'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4F46E5 100%)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background decoration */}
      <Box sx={{
        position: 'absolute', top: '-20%', right: '-10%',
        width: 600, height: 600, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(129,140,248,0.15) 0%, transparent 70%)',
      }} />
      <Box sx={{
        position: 'absolute', bottom: '-20%', left: '-10%',
        width: 500, height: 500, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(167,139,250,0.15) 0%, transparent 70%)',
      }} />

      <Container maxWidth="sm" sx={{ position: 'relative', zIndex: 1 }}>
        <Card sx={{
          width: '100%', maxWidth: 440, mx: 'auto',
          borderRadius: 4,
          boxShadow: '0 25px 60px rgba(0,0,0,0.3)',
          border: '1px solid rgba(255,255,255,0.1)',
        }}>
          <CardContent sx={{ p: 4 }}>
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <Box sx={{
                width: 60, height: 60, borderRadius: '16px', mx: 'auto', mb: 2,
                background: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 8px 24px rgba(79,70,229,0.35)',
              }}>
                <SmartToy sx={{ fontSize: 32, color: '#fff' }} />
              </Box>
              <Typography variant="h4" fontWeight={800} sx={{ letterSpacing: '-0.02em' }}>
                {t('app.name')}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {t('app.subtitle')}
              </Typography>
            </Box>
            {error && <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>{error}</Alert>}
            <form onSubmit={handleSubmit}>
              <TextField fullWidth label={t('auth.email')} type="email" value={email}
                onChange={(e) => setEmail(e.target.value)} margin="normal" required
                autoComplete="email" autoFocus inputProps={{ 'aria-label': t('auth.email') }} />
              <TextField fullWidth label={t('auth.password')} type="password" value={password}
                onChange={(e) => setPassword(e.target.value)} margin="normal" required
                autoComplete="current-password" inputProps={{ 'aria-label': t('auth.password') }} />
              <Button fullWidth variant="contained" size="large" type="submit" disabled={loading}
                sx={{ mt: 3, mb: 2, py: 1.5, fontSize: '1rem', fontWeight: 600, borderRadius: 3 }}>
                {loading ? t('common.loading') : t('auth.loginButton')}
              </Button>
            </form>
            <FormControl fullWidth size="small" sx={{ mt: 1 }}>
              <InputLabel>{t('settings.language')}</InputLabel>
              <Select value={i18n.language?.substring(0, 2) || 'en'} label={t('settings.language')}
                onChange={(e) => i18n.changeLanguage(e.target.value)}>
                <MenuItem value="en">English</MenuItem>
                <MenuItem value="fr">Français</MenuItem>
                <MenuItem value="es">Español</MenuItem>
              </Select>
            </FormControl>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
};

export default LoginPage;
