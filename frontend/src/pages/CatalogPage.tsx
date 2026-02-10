import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Grid, Card, CardContent, CardActions, Button,
  Chip, TextField, InputAdornment, alpha, useTheme, Avatar,
} from '@mui/material';
import { Search, SmartToy, OpenInNew, Psychology, Memory, AccountTree, Build } from '@mui/icons-material';
import api from '../services/api';

const AGENT_TYPE_CONFIG: Record<string, { icon: React.ReactElement; gradient: string; color: string }> = {
  conversational: { icon: <Psychology />, gradient: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)', color: '#4F46E5' },
  rag: { icon: <Memory />, gradient: 'linear-gradient(135deg, #059669 0%, #10B981 100%)', color: '#059669' },
  workflow: { icon: <AccountTree />, gradient: 'linear-gradient(135deg, #D97706 0%, #F59E0B 100%)', color: '#D97706' },
  custom: { icon: <Build />, gradient: 'linear-gradient(135deg, #DC2626 0%, #EF4444 100%)', color: '#DC2626' },
};

const CatalogPage: React.FC = () => {
  const { t } = useTranslation();
  const theme = useTheme();
  const [agents, setAgents] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string | null>(null);

  const fetchAgents = useCallback(async () => {
    try { const res = await api.get('/api/agents'); setAgents(res.data); } catch {}
  }, []);

  useEffect(() => { fetchAgents(); }, [fetchAgents]);

  const filtered = agents.filter(a => {
    const matchesSearch = a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.description?.toLowerCase().includes(search.toLowerCase());
    const matchesType = !filterType || a.agent_type === filterType;
    return matchesSearch && matchesType;
  });

  const agentTypes = Array.from(new Set(agents.map(a => a.agent_type)));

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>{t('agents.title')}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {filtered.length} agent{filtered.length !== 1 ? 's' : ''}
          </Typography>
        </Box>
      </Box>

      <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
        <TextField
          placeholder={t('common.search')}
          value={search}
          onChange={e => setSearch(e.target.value)}
          InputProps={{
            startAdornment: <InputAdornment position="start"><Search color="action" /></InputAdornment>,
          }}
          size="small"
          sx={{ minWidth: 300, '& .MuiOutlinedInput-root': { bgcolor: 'background.paper' } }}
        />
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Chip
            label={t('common.all') || 'Tous'}
            onClick={() => setFilterType(null)}
            variant={!filterType ? 'filled' : 'outlined'}
            color={!filterType ? 'primary' : 'default'}
            sx={{ fontWeight: 500 }}
          />
          {agentTypes.map(type => (
            <Chip
              key={type}
              label={t(`agents.${type}`) || type}
              onClick={() => setFilterType(filterType === type ? null : type)}
              variant={filterType === type ? 'filled' : 'outlined'}
              color={filterType === type ? 'primary' : 'default'}
              sx={{ fontWeight: 500 }}
            />
          ))}
        </Box>
      </Box>

      <Grid container spacing={3}>
        {filtered.map(agent => {
          const config = AGENT_TYPE_CONFIG[agent.agent_type] || AGENT_TYPE_CONFIG.custom;
          return (
            <Grid item xs={12} sm={6} md={4} key={agent.id}>
              <Card sx={{
                height: '100%', display: 'flex', flexDirection: 'column',
                position: 'relative', overflow: 'hidden',
                '&:hover': { transform: 'translateY(-2px)' },
                transition: 'all 0.2s ease',
              }}>
                <Box sx={{ height: 4, background: config.gradient }} />
                <CardContent sx={{ flex: 1, pt: 2.5, pb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
                    <Avatar sx={{
                      width: 44, height: 44,
                      background: config.gradient,
                      borderRadius: '12px',
                      boxShadow: `0 4px 12px ${alpha(config.color, 0.3)}`,
                    }} variant="rounded">
                      {config.icon}
                    </Avatar>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography variant="subtitle1" fontWeight={600} color="text.primary" noWrap>
                        {agent.name}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 0.5, mt: 0.25 }}>
                        <Chip label={t(`agents.${agent.agent_type}`) || agent.agent_type} size="small" color="primary" sx={{ height: 22, fontSize: '0.7rem' }} />
                        <Chip label={`v${agent.version}`} size="small" variant="outlined" sx={{ height: 22, fontSize: '0.7rem' }} />
                      </Box>
                    </Box>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{
                    overflow: 'hidden', textOverflow: 'ellipsis',
                    display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical',
                    lineHeight: 1.6,
                  }}>
                    {agent.description || t('common.noData')}
                  </Typography>
                </CardContent>
                <CardActions sx={{ px: 2, pb: 2, pt: 0 }}>
                  <Button size="small" variant="outlined" fullWidth endIcon={<OpenInNew sx={{ fontSize: '16px !important' }} />} sx={{ borderRadius: 2 }}>
                    {t('common.edit')}
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          );
        })}
        {filtered.length === 0 && (
          <Grid item xs={12}>
            <Box sx={{
              py: 8, textAlign: 'center', borderRadius: 4,
              bgcolor: alpha(theme.palette.primary.main, 0.04),
              border: `1px dashed ${theme.palette.divider}`,
            }}>
              <SmartToy sx={{ fontSize: 48, color: 'text.secondary', mb: 1, opacity: 0.5 }} />
              <Typography color="text.secondary">{t('common.noData')}</Typography>
            </Box>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default CatalogPage;
