import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Card, CardContent, Grid, FormControl, InputLabel,
  Select, MenuItem, Button, Chip, Alert, alpha, useTheme, IconButton, Tooltip,
} from '@mui/material';
import { SmartToy, RestartAlt } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

interface Provider {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  models: Model[];
}

interface Model {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
}

interface AgentInfo {
  slug: string;
  name: string;
  description: string;
  icon: string;
}

interface AgentConfig {
  agent_slug: string;
  provider_id: string;
  model_id: string;
  provider_name?: string;
  model_name?: string;
}

const AgentLLMConfigPage: React.FC = () => {
  const { t } = useTranslation();
  const theme = useTheme();
  const { enqueueSnackbar } = useSnackbar();

  const [providers, setProviders] = useState<Provider[]>([]);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [configs, setConfigs] = useState<Record<string, AgentConfig>>({});
  const [selections, setSelections] = useState<Record<string, { provider_id: string; model_id: string }>>({});

  const fetchProviders = useCallback(async () => {
    try {
      const res = await api.get('/api/llm/providers');
      setProviders(res.data);
    } catch { /* empty */ }
  }, []);

  const fetchAgents = useCallback(async () => {
    try {
      const res = await api.get('/api/agent-runtime/catalog');
      setAgents(res.data);
    } catch { /* empty */ }
  }, []);

  const fetchConfigs = useCallback(async () => {
    try {
      const res = await api.get('/api/agent-runtime/config/llm');
      const map: Record<string, AgentConfig> = {};
      for (const c of res.data) {
        map[c.agent_slug] = c;
      }
      setConfigs(map);
      // Initialize selections from existing configs
      const sel: Record<string, { provider_id: string; model_id: string }> = {};
      for (const c of res.data) {
        sel[c.agent_slug] = { provider_id: c.provider_id, model_id: c.model_id };
      }
      setSelections(sel);
    } catch { /* empty */ }
  }, []);

  useEffect(() => {
    fetchProviders();
    fetchAgents();
    fetchConfigs();
  }, [fetchProviders, fetchAgents, fetchConfigs]);

  const handleProviderChange = (agentSlug: string, providerId: string) => {
    setSelections(prev => ({
      ...prev,
      [agentSlug]: { provider_id: providerId, model_id: '' },
    }));
  };

  const handleModelChange = (agentSlug: string, modelId: string) => {
    setSelections(prev => ({
      ...prev,
      [agentSlug]: { ...prev[agentSlug], model_id: modelId },
    }));
  };

  const handleSave = async (agentSlug: string) => {
    const sel = selections[agentSlug];
    if (!sel?.provider_id || !sel?.model_id) return;
    try {
      await api.put(`/api/agent-runtime/config/llm/${agentSlug}`, {
        provider_id: sel.provider_id,
        model_id: sel.model_id,
      });
      enqueueSnackbar(t('agentLlmConfig.saved', { agent: agentSlug }), { variant: 'success' });
      fetchConfigs();
    } catch {
      enqueueSnackbar(t('common.error'), { variant: 'error' });
    }
  };

  const handleReset = async (agentSlug: string) => {
    try {
      await api.delete(`/api/agent-runtime/config/llm/${agentSlug}`);
      setSelections(prev => {
        const next = { ...prev };
        delete next[agentSlug];
        return next;
      });
      enqueueSnackbar(t('agentLlmConfig.deleted', { agent: agentSlug }), { variant: 'info' });
      fetchConfigs();
    } catch {
      enqueueSnackbar(t('common.error'), { variant: 'error' });
    }
  };

  const activeProviders = providers.filter(p => p.is_active);

  if (activeProviders.length === 0) {
    return (
      <Alert severity="info" sx={{ borderRadius: 2 }}>
        {t('agentLlmConfig.noProviders')}
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t('agentLlmConfig.description')}
      </Typography>

      <Grid container spacing={2}>
        {agents.map(agent => {
          const currentConfig = configs[agent.slug];
          const sel = selections[agent.slug] || { provider_id: '', model_id: '' };
          const selectedProvider = activeProviders.find(p => p.id === sel.provider_id);
          const availableModels = selectedProvider?.models.filter(m => m.is_active) || [];
          const hasChanges = currentConfig
            ? sel.provider_id !== currentConfig.provider_id || sel.model_id !== currentConfig.model_id
            : !!(sel.provider_id && sel.model_id);

          return (
            <Grid item xs={12} key={agent.slug}>
              <Card sx={{
                border: currentConfig ? `1px solid ${alpha(theme.palette.success.main, 0.4)}` : undefined,
                transition: 'border-color 0.2s',
              }}>
                <CardContent sx={{ py: 2, px: 3, '&:last-child': { pb: 2 } }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
                    {/* Agent info */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 200 }}>
                      <SmartToy fontSize="small" color="primary" />
                      <Box>
                        <Typography variant="subtitle2" fontWeight={600}>{agent.name}</Typography>
                        <Typography variant="caption" color="text.secondary">{agent.slug}</Typography>
                      </Box>
                      {currentConfig && (
                        <Chip
                          label={t('agentLlmConfig.configured')}
                          size="small"
                          color="success"
                          variant="outlined"
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>

                    {/* Provider select */}
                    <FormControl size="small" sx={{ minWidth: 200, flex: 1 }}>
                      <InputLabel>{t('agentLlmConfig.provider')}</InputLabel>
                      <Select
                        value={sel.provider_id}
                        label={t('agentLlmConfig.provider')}
                        onChange={e => handleProviderChange(agent.slug, e.target.value)}
                      >
                        <MenuItem value="">
                          <em>{t('agentLlmConfig.platformDefault')}</em>
                        </MenuItem>
                        {activeProviders.map(p => (
                          <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    {/* Model select */}
                    <FormControl size="small" sx={{ minWidth: 200, flex: 1 }}>
                      <InputLabel>{t('agentLlmConfig.model')}</InputLabel>
                      <Select
                        value={sel.model_id}
                        label={t('agentLlmConfig.model')}
                        disabled={!sel.provider_id}
                        onChange={e => handleModelChange(agent.slug, e.target.value)}
                      >
                        {availableModels.map(m => (
                          <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    {/* Actions */}
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button
                        variant="contained"
                        size="small"
                        disabled={!hasChanges || !sel.provider_id || !sel.model_id}
                        onClick={() => handleSave(agent.slug)}
                        sx={{ borderRadius: 2, textTransform: 'none' }}
                      >
                        {t('common.save')}
                      </Button>
                      {currentConfig && (
                        <Tooltip title={t('agentLlmConfig.reset')}>
                          <IconButton
                            size="small"
                            color="warning"
                            onClick={() => handleReset(agent.slug)}
                          >
                            <RestartAlt fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>
    </Box>
  );
};

export default AgentLLMConfigPage;
