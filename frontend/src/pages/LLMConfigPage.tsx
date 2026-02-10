import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Card, CardContent, CardActions, Grid, Chip, IconButton,
  Accordion, AccordionSummary, AccordionDetails, Switch, FormControlLabel, List,
  ListItem, ListItemText, ListItemSecondaryAction,
} from '@mui/material';
import { Add, Edit, Delete, VpnKey, ExpandMore, CheckCircle, Cancel } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

interface LLMModel { id: string; name: string; slug: string; is_active: boolean; }
interface Provider { id: string; name: string; slug: string; base_url: string | null; is_active: boolean; models: LLMModel[]; has_api_key: boolean; }

const LLMConfigPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [providerDialog, setProviderDialog] = useState(false);
  const [modelDialog, setModelDialog] = useState(false);
  const [apiKeyDialog, setApiKeyDialog] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [providerForm, setProviderForm] = useState({ name: '', slug: '', base_url: '', is_active: true });
  const [modelForm, setModelForm] = useState({ name: '', slug: '', is_active: true });
  const [apiKey, setApiKey] = useState('');

  const fetchProviders = useCallback(async () => {
    try {
      const res = await api.get('/api/llm/providers');
      setProviders(res.data);
    } catch {}
  }, []);

  useEffect(() => { fetchProviders(); }, [fetchProviders]);

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
      if (editingProvider) {
        await api.put(`/api/llm/providers/${editingProvider.id}`, providerForm);
      } else {
        await api.post('/api/llm/providers', providerForm);
      }
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
    try {
      await api.delete(`/api/llm/models/${modelId}`);
      fetchProviders();
    } catch {}
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight={600}>{t('llm.title')}</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => openProviderDialog()}>{t('llm.addProvider')}</Button>
      </Box>
      <Grid container spacing={3}>
        {providers.map(provider => (
          <Grid item xs={12} md={6} key={provider.id}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="h6">{provider.name}</Typography>
                  <Chip label={provider.is_active ? t('common.active') : t('common.inactive')} color={provider.is_active ? 'success' : 'default'} size="small" />
                </Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>{provider.slug}</Typography>
                {provider.base_url && <Typography variant="body2" color="text.secondary">{provider.base_url}</Typography>}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                  {provider.has_api_key ? <Chip icon={<CheckCircle />} label={t('llm.apiKeySet')} color="success" size="small" /> : <Chip icon={<Cancel />} label={t('llm.apiKeyNotSet')} color="warning" size="small" />}
                </Box>
                <Accordion sx={{ mt: 2 }}>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography>{t('llm.models')} ({provider.models.length})</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <List dense>
                      {provider.models.map(model => (
                        <ListItem key={model.id}>
                          <ListItemText primary={model.name} secondary={model.slug} />
                          <ListItemSecondaryAction>
                            <IconButton size="small" onClick={() => deleteModel(model.id)} aria-label={t('common.delete')}><Delete fontSize="small" /></IconButton>
                          </ListItemSecondaryAction>
                        </ListItem>
                      ))}
                    </List>
                    <Button size="small" onClick={() => { setSelectedProvider(provider); setModelDialog(true); }}>{t('llm.addModel')}</Button>
                  </AccordionDetails>
                </Accordion>
              </CardContent>
              <CardActions>
                <Button size="small" startIcon={<VpnKey />} onClick={() => { setSelectedProvider(provider); setApiKeyDialog(true); }}>{t('llm.setApiKey')}</Button>
                <Button size="small" startIcon={<Edit />} onClick={() => openProviderDialog(provider)}>{t('common.edit')}</Button>
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
          <FormControlLabel control={<Switch checked={providerForm.is_active} onChange={e => setProviderForm({ ...providerForm, is_active: e.target.checked })} />} label={t('common.active')} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setProviderDialog(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={saveProvider}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={apiKeyDialog} onClose={() => setApiKeyDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('llm.setApiKey')} - {selectedProvider?.name}</DialogTitle>
        <DialogContent>
          <TextField fullWidth label={t('llm.apiKey')} value={apiKey} onChange={e => setApiKey(e.target.value)} margin="normal" type="password" autoComplete="off" />
        </DialogContent>
        <DialogActions>
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
        <DialogActions>
          <Button onClick={() => setModelDialog(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={addModel}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LLMConfigPage;
