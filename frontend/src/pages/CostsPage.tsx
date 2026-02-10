import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Card, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, IconButton, alpha, useTheme, Tooltip,
} from '@mui/material';
import { Add, Edit, Delete } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

const CostsPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const [costs, setCosts] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState({ model_id: '', cost_per_token_in: 0, cost_per_token_out: 0, effective_date: '' });

  const fetchCosts = useCallback(async () => {
    try { const res = await api.get('/api/costs'); setCosts(res.data); } catch {}
  }, []);

  useEffect(() => { fetchCosts(); }, [fetchCosts]);

  const handleOpen = (cost?: any) => {
    if (cost) {
      setEditing(cost);
      setForm({ model_id: cost.model_id, cost_per_token_in: cost.cost_per_token_in, cost_per_token_out: cost.cost_per_token_out, effective_date: cost.effective_date });
    } else {
      setEditing(null);
      setForm({ model_id: '', cost_per_token_in: 0, cost_per_token_out: 0, effective_date: new Date().toISOString().split('T')[0] });
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
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8em' }}>{c.model_id}</TableCell>
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
          <TextField fullWidth label="Model ID (UUID)" value={form.model_id} onChange={e => setForm({ ...form, model_id: e.target.value })} margin="normal" required disabled={!!editing} />
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
