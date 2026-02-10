import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Box, Card, CardContent, TextField, Button, Typography, Alert,
  Container, Select, MenuItem, FormControl, InputLabel,
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
    <Container maxWidth="sm">
      <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Card sx={{ width: '100%', maxWidth: 440 }}>
          <CardContent sx={{ p: 4 }}>
            <Box sx={{ textAlign: 'center', mb: 3 }}>
              <SmartToy sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
              <Typography variant="h4" fontWeight={700}>{t('app.name')}</Typography>
              <Typography variant="body2" color="text.secondary">{t('app.subtitle')}</Typography>
            </Box>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            <form onSubmit={handleSubmit}>
              <TextField fullWidth label={t('auth.email')} type="email" value={email}
                onChange={(e) => setEmail(e.target.value)} margin="normal" required
                autoComplete="email" autoFocus inputProps={{ 'aria-label': t('auth.email') }} />
              <TextField fullWidth label={t('auth.password')} type="password" value={password}
                onChange={(e) => setPassword(e.target.value)} margin="normal" required
                autoComplete="current-password" inputProps={{ 'aria-label': t('auth.password') }} />
              <Button fullWidth variant="contained" size="large" type="submit" disabled={loading}
                sx={{ mt: 3, mb: 2, py: 1.5 }}>
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
      </Box>
    </Container>
  );
};

export default LoginPage;
