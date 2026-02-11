import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Card, CardContent, CardActions, Grid, Chip, IconButton,
  Accordion, AccordionSummary, AccordionDetails, Switch, FormControlLabel, List,
  ListItem, ListItemText, ListItemSecondaryAction, alpha, useTheme, Avatar, Tooltip,
  CircularProgress, Alert,
} from '@mui/material';
import { Add, Edit, Delete, VpnKey, ExpandMore, CheckCircle, Cancel, Cloud, Sync } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

interface LLMModel { id: string; name: string; slug: string; is_active: boolean; }
interface Provider { id: string; name: string; slug: string; base_url: string | null; is_active: boolean; models: LLMModel[]; has_api_key: boolean; }

const PROVIDER_COLORS = [
  'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)',
  'linear-gradient(135deg, #059669 0%, #10B981 100%)',
  'linear-gradient(135deg, #D97706 0%, #F59E0B 100%)',
  'linear-gradient(135deg, #DC2626 0%, #EF4444 100%)',
  'linear-gradient(135deg, #2563EB 0%, #3B82F6 100%)',
  'linear-gradient(135deg, #7C3AED 0%, #EC4899 100%)',
  'linear-gradient(135deg, #0891B2 0%, #06B6D4 100%)',
];

const LLMConfigPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [providerDialog, setProviderDialog] = useState(false);
  const [modelDialog, setModelDialog] = useState(false);
  const [apiKeyDialog, setApiKeyDialog] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [providerForm, setProviderForm] = useState({ name: '', slug: '', base_url: '', is_active: true });
  const [modelForm, setModelForm] = useState({ name: '', slug: '', is_active: true });
  const [apiKey, setApiKey] = useState('');
  const [syncing, setSyncing] = useState(false);

  const fetchProviders = useCallback(async () => {
    try { const res = await api.get('/api/llm/providers'); setProviders(res.data); } catch {}
  }, []);

  useEffect(() => { fetchProviders(); }, [fetchProviders]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await api.post('/api/llm/sync');
      const { providers_created, models_created } = res.data;
      if (providers_created > 0 || models_created > 0) {
        enqueueSnackbar(t('llm.syncSuccess', { providers: providers_created, models: models_created }), { variant: 'success' });
      } else {
        enqueueSnackbar(t('llm.syncUpToDate'), { variant: 'info' });
      }
      fetchProviders();
    } catch (e: any) {
      enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' });
    }
    setSyncing(false);
  };

  const openProviderDialog = (provider?: Provider) => {
    if (provider) {
      setEditingProvider(provider);
      setProviderForm({ name: provider.name, slug: provider.slug, base_url: provider.base_url || '', is_active: provider.is_active });
    } else {
      setEditingProvider(null);
      setProviderForm({ name: '', slug: '', base_url: '', is_active: true });
    }
    setProviderDialog(true);
  };

  const saveProvider = async () => {
    try {
      if (editingProvider) { await api.put(`/api/llm/providers/${editingProvider.id}`, providerForm); }
      else { await api.post('/api/llm/providers', providerForm); }
      setProviderDialog(false);
      fetchProviders();
      enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) {
      enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' });
    }
  };

  const saveApiKey = async () => {
    if (!selectedProvider) return;
    try {
      await api.post(`/api/llm/providers/${selectedProvider.id}/api-key`, { api_key: apiKey });
      setApiKeyDialog(false);
      setApiKey('');
      fetchProviders();
      enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) {
      enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' });
    }
  };

  const addModel = async () => {
    if (!selectedProvider) return;
    try {
      await api.post(`/api/llm/providers/${selectedProvider.id}/models`, modelForm);
      setModelDialog(false);
      setModelForm({ name: '', slug: '', is_active: true });
      fetchProviders();
      enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) {
      enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' });
    }
  };

  const deleteModel = async (modelId: string) => {
    try { await api.delete(`/api/llm/models/${modelId}`); fetchProviders(); } catch {}
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>{t('llm.title')}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {providers.length} provider{providers.length !== 1 ? 's' : ''} &middot; {providers.reduce((acc, p) => acc + p.models.length, 0)} {t('llm.models').toLowerCase()}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1.5 }}>
          <Tooltip title={t('llm.syncTooltip')}>
            <Button
              variant="outlined"
              startIcon={syncing ? <CircularProgress size={18} /> : <Sync />}
              onClick={handleSync}
              disabled={syncing}
            >
              {t('llm.syncConnectors')}
            </Button>
          </Tooltip>
          <Button variant="contained" startIcon={<Add />} onClick={() => openProviderDialog()} sx={{ px: 3 }}>
            {t('llm.addProvider')}
          </Button>
        </Box>
      </Box>

      {providers.length === 0 && (
        <Alert
          severity="info"
          sx={{ mb: 3, borderRadius: 2 }}
          action={
            <Button size="small" variant="outlined" onClick={handleSync} disabled={syncing} startIcon={syncing ? <CircularProgress size={16} /> : <Sync />}>
              {t('llm.syncConnectors')}
            </Button>
          }
        >
          {t('llm.emptyState')}
        </Alert>
      )}

      <Grid container spacing={3}>
        {providers.map((provider, index) => (
          <Grid item xs={12} md={6} key={provider.id}>
            <Card sx={{
              overflow: 'hidden',
              '&:hover': { transform: 'translateY(-2px)' },
              transition: 'all 0.2s ease',
            }}>
              <Box sx={{ height: 4, background: PROVIDER_COLORS[index % PROVIDER_COLORS.length] }} />
              <CardContent sx={{ pt: 2.5 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Avatar variant="rounded" sx={{
                      width: 44, height: 44,
                      background: PROVIDER_COLORS[index % PROVIDER_COLORS.length],
                      borderRadius: '12px',
                    }}>
                      <Cloud />
                    </Avatar>
                    <Box>
                      <Typography variant="subtitle1" fontWeight={700}>{provider.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{provider.slug}</Typography>
                    </Box>
                  </Box>
                  <Chip
                    label={provider.is_active ? t('common.active') : t('common.inactive')}
                    color={provider.is_active ? 'success' : 'default'}
                    size="small"
                  />
                </Box>

                {provider.base_url && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontFamily: 'monospace', fontSize: '0.8rem' }}>
                    {provider.base_url}
                  </Typography>
                )}

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  {provider.has_api_key ? (
                    <Chip icon={<CheckCircle />} label={t('llm.apiKeySet')} color="success" size="small" />
                  ) : (
                    <Chip icon={<Cancel />} label={t('llm.apiKeyNotSet')} color="warning" size="small" />
                  )}
                </Box>

                <Accordion sx={{ mt: 1 }}>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography fontWeight={500}>{t('llm.models')}</Typography>
                      <Chip label={provider.models.length} size="small" color="primary" sx={{ height: 22, fontSize: '0.7rem' }} />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <List dense disablePadding>
                      {provider.models.map(model => (
                        <ListItem key={model.id} sx={{
                          borderRadius: 2, mb: 0.5,
                          bgcolor: alpha(theme.palette.primary.main, 0.04),
                        }}>
                          <ListItemText
                            primary={<Typography variant="body2" fontWeight={500}>{model.name}</Typography>}
                            secondary={model.slug}
                          />
                          <ListItemSecondaryAction>
                            <Tooltip title={t('common.delete')}>
                              <IconButton size="small" onClick={() => deleteModel(model.id)} sx={{ color: 'error.main' }}>
                                <Delete fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </ListItemSecondaryAction>
                        </ListItem>
                      ))}
                    </List>
                    <Button size="small" onClick={() => { setSelectedProvider(provider); setModelDialog(true); }} sx={{ mt: 1 }}>
                      {t('llm.addModel')}
                    </Button>
                  </AccordionDetails>
                </Accordion>
              </CardContent>
              <CardActions sx={{ px: 2, pb: 2, gap: 1 }}>
                <Button size="small" variant="outlined" startIcon={<VpnKey />}
                  onClick={() => { setSelectedProvider(provider); setApiKeyDialog(true); }}>
                  {t('llm.setApiKey')}
                </Button>
                <Button size="small" variant="outlined" startIcon={<Edit />}
                  onClick={() => openProviderDialog(provider)}>
                  {t('common.edit')}
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog open={providerDialog} onClose={() => setProviderDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingProvider ? t('llm.editProvider') : t('llm.addProvider')}</DialogTitle>
        <DialogContent>
          <TextField fullWidth label={t('agents.name')} value={providerForm.name} onChange={e => setProviderForm({ ...providerForm, name: e.target.value })} margin="normal" required />
          <TextField fullWidth label={t('llm.slug')} value={providerForm.slug} onChange={e => setProviderForm({ ...providerForm, slug: e.target.value })} margin="normal" required />
          <TextField fullWidth label={t('llm.baseUrl')} value={providerForm.base_url} onChange={e => setProviderForm({ ...providerForm, base_url: e.target.value })} margin="normal" />
          <FormControlLabel control={<Switch checked={providerForm.is_active} onChange={e => setProviderForm({ ...providerForm, is_active: e.target.checked })} />} label={t('common.active')} sx={{ mt: 1 }} />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setProviderDialog(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={saveProvider}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={apiKeyDialog} onClose={() => setApiKeyDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('llm.setApiKey')} - {selectedProvider?.name}</DialogTitle>
        <DialogContent>
          <TextField fullWidth label={t('llm.apiKey')} value={apiKey} onChange={e => setApiKey(e.target.value)} margin="normal" type="password" autoComplete="off" />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setApiKeyDialog(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={saveApiKey}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={modelDialog} onClose={() => setModelDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('llm.addModel')}</DialogTitle>
        <DialogContent>
          <TextField fullWidth label={t('agents.name')} value={modelForm.name} onChange={e => setModelForm({ ...modelForm, name: e.target.value })} margin="normal" required />
          <TextField fullWidth label={t('llm.slug')} value={modelForm.slug} onChange={e => setModelForm({ ...modelForm, slug: e.target.value })} margin="normal" required />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setModelDialog(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={addModel}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LLMConfigPage;
