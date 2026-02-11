import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Card, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, IconButton, alpha, useTheme, Tooltip, FormControl, InputLabel,
  Select, MenuItem,
} from '@mui/material';
import { Add, Edit, Delete } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

const CostsPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const [costs, setCosts] = useState<any[]>([]);
  const [providers, setProviders] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState({ model_id: '', cost_per_token_in: 0, cost_per_token_out: 0, effective_date: '' });
  const [selectedProviderId, setSelectedProviderId] = useState('');

  const fetchCosts = useCallback(async () => {
    try { const res = await api.get('/api/costs'); setCosts(res.data); } catch {}
  }, []);
  const fetchProviders = useCallback(async () => {
    try { const res = await api.get('/api/llm/providers'); setProviders(res.data); } catch {}
  }, []);

  useEffect(() => { fetchCosts(); fetchProviders(); }, [fetchCosts, fetchProviders]);

  const modelMap = React.useMemo(() => {
    const map: Record<string, { name: string; provider: string }> = {};
    for (const p of providers) {
      for (const m of (p.models || [])) {
        map[m.id] = { name: m.name, provider: p.name };
      }
    }
    return map;
  }, [providers]);

  const selectedProviderModels = React.useMemo(() => {
    const provider = providers.find((p: any) => p.id === selectedProviderId);
    return provider?.models || [];
  }, [providers, selectedProviderId]);

  const handleOpen = (cost?: any) => {
    if (cost) {
      setEditing(cost);
      setForm({ model_id: cost.model_id, cost_per_token_in: cost.cost_per_token_in, cost_per_token_out: cost.cost_per_token_out, effective_date: cost.effective_date });
      const info = modelMap[cost.model_id];
      if (info) {
        const prov = providers.find((p: any) => p.name === info.provider);
        if (prov) setSelectedProviderId(prov.id);
      }
    } else {
      setEditing(null);
      setForm({ model_id: '', cost_per_token_in: 0, cost_per_token_out: 0, effective_date: new Date().toISOString().split('T')[0] });
      setSelectedProviderId('');
    }
    setOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editing) { await api.put(`/api/costs/${editing.id}`, form); }
      else { await api.post('/api/costs', form); }
      setOpen(false); fetchCosts();
      enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) { enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' }); }
  };

  const handleDelete = async (id: string) => {
    try { await api.delete(`/api/costs/${id}`); fetchCosts(); } catch {}
  };

  const renderModelName = (modelId: string) => {
    const info = modelMap[modelId];
    if (info) return <><Typography variant="body2" fontWeight={500}>{info.name}</Typography><Typography variant="caption" color="text.secondary">{info.provider}</Typography></>;
    return <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8em' }}>{modelId}</Typography>;
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>{t('costs.title')}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {costs.length} cost configuration{costs.length !== 1 ? 's' : ''}
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<Add />} onClick={() => handleOpen()} sx={{ px: 3 }}>
          {t('costs.create')}
        </Button>
      </Box>

      <Card>
        <TableContainer>
          <Table aria-label={t('costs.title')}>
            <TableHead>
              <TableRow>
                <TableCell>{t('costs.model')}</TableCell>
                <TableCell>{t('costs.costPerTokenIn')}</TableCell>
                <TableCell>{t('costs.costPerTokenOut')}</TableCell>
                <TableCell>{t('costs.effectiveDate')}</TableCell>
                <TableCell align="right">{t('common.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {costs.map((c: any) => (
                <TableRow key={c.id} hover>
                  <TableCell>{renderModelName(c.model_id)}</TableCell>
                  <TableCell><Typography variant="body2" fontWeight={500} sx={{ fontFamily: 'monospace' }}>${c.cost_per_token_in?.toFixed(8)}</Typography></TableCell>
                  <TableCell><Typography variant="body2" fontWeight={500} sx={{ fontFamily: 'monospace' }}>${c.cost_per_token_out?.toFixed(8)}</Typography></TableCell>
                  <TableCell>{c.effective_date}</TableCell>
                  <TableCell align="right">
                    <Tooltip title={t('common.edit')}>
                      <IconButton size="small" onClick={() => handleOpen(c)} sx={{
                        bgcolor: alpha(theme.palette.primary.main, 0.08), mr: 0.5,
                        '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.15) },
                      }}><Edit fontSize="small" /></IconButton>
                    </Tooltip>
                    <Tooltip title={t('common.delete')}>
                      <IconButton size="small" color="error" onClick={() => handleDelete(c.id)} sx={{
                        bgcolor: alpha(theme.palette.error.main, 0.08),
                        '&:hover': { bgcolor: alpha(theme.palette.error.main, 0.15) },
                      }}><Delete fontSize="small" /></IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing ? t('costs.edit') : t('costs.create')}</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="normal" required disabled={!!editing}>
            <InputLabel>{t('costs.provider')}</InputLabel>
            <Select
              value={selectedProviderId}
              label={t('costs.provider')}
              onChange={e => {
                setSelectedProviderId(e.target.value as string);
                setForm({ ...form, model_id: '' });
              }}
            >
              {providers.map((p: any) => (
                <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth margin="normal" required disabled={!!editing || !selectedProviderId}>
            <InputLabel>{t('costs.model')}</InputLabel>
            <Select
              value={form.model_id}
              label={t('costs.model')}
              onChange={e => setForm({ ...form, model_id: e.target.value as string })}
            >
              {selectedProviderModels.map((m: any) => (
                <MenuItem key={m.id} value={m.id}>
                  <Box>
                    <Typography variant="body2">{m.name}</Typography>
                    <Typography variant="caption" color="text.secondary">{m.slug}</Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField fullWidth label={t('costs.costPerTokenIn')} type="number" value={form.cost_per_token_in} onChange={e => setForm({ ...form, cost_per_token_in: parseFloat(e.target.value) })} margin="normal" inputProps={{ step: 0.000001 }} />
          <TextField fullWidth label={t('costs.costPerTokenOut')} type="number" value={form.cost_per_token_out} onChange={e => setForm({ ...form, cost_per_token_out: parseFloat(e.target.value) })} margin="normal" inputProps={{ step: 0.000001 }} />
          <TextField fullWidth label={t('costs.effectiveDate')} type="date" value={form.effective_date} onChange={e => setForm({ ...form, effective_date: e.target.value })} margin="normal" InputLabelProps={{ shrink: true }} />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={handleSave}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CostsPage;
