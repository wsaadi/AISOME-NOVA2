import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Grid, Card, CardContent, CardActions, Button,
  Chip, TextField, InputAdornment,
} from '@mui/material';
import { Search, SmartToy } from '@mui/icons-material';
import api from '../services/api';

const CatalogPage: React.FC = () => {
  const { t } = useTranslation();
  const [agents, setAgents] = useState<any[]>([]);
  const [search, setSearch] = useState('');

  const fetchAgents = useCallback(async () => {
    try { const res = await api.get('/api/agents'); setAgents(res.data); } catch {}
  }, []);

  useEffect(() => { fetchAgents(); }, [fetchAgents]);

  const filtered = agents.filter(a =>
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    a.description?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Box>
      <Typography variant="h4" fontWeight={600} gutterBottom>{t('agents.title')}</Typography>
      <TextField fullWidth placeholder={t('common.search')} value={search} onChange={e => setSearch(e.target.value)}
        InputProps={{ startAdornment: <InputAdornment position="start"><Search /></InputAdornment> }}
        sx={{ mb: 3 }} size="small" />
      <Grid container spacing={3}>
        {filtered.map(agent => (
          <Grid item xs={12} sm={6} md={4} key={agent.id}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flex: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <SmartToy color="primary" />
                  <Typography variant="h6">{agent.name}</Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 0.5, mb: 1, flexWrap: 'wrap' }}>
                  <Chip label={t(`agents.${agent.agent_type}`) || agent.agent_type} size="small" color="primary" variant="outlined" />
                  <Chip label={`v${agent.version}`} size="small" variant="outlined" />
                </Box>
                <Typography variant="body2" color="text.secondary">{agent.description || t('common.noData')}</Typography>
              </CardContent>
              <CardActions>
                <Button size="small" color="primary">{t('common.edit')}</Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
        {filtered.length === 0 && (
          <Grid item xs={12}>
            <Typography color="text.secondary" textAlign="center" sx={{ py: 4 }}>{t('common.noData')}</Typography>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default CatalogPage;
