import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Card, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, IconButton, FormControl, InputLabel, Select, MenuItem, Chip,
} from '@mui/material';
import { Add, Edit, Delete } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

const QuotasPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const [quotas, setQuotas] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState({ target_type: 'user', target_id: '', quota_type: 'token', period: 'month', limit_value: 0, is_active: true });

  const fetchQuotas = useCallback(async () => {
    try { const res = await api.get('/api/quotas'); setQuotas(res.data); } catch {}
  }, []);

  useEffect(() => { fetchQuotas(); }, [fetchQuotas]);

  const handleOpen = (quota?: any) => {
    if (quota) {
      setEditing(quota);
      setForm({ target_type: quota.target_type, target_id: quota.target_id, quota_type: quota.quota_type, period: quota.period, limit_value: quota.limit_value, is_active: quota.is_active });
    } else {
      setEditing(null);
      setForm({ target_type: 'user', target_id: '', quota_type: 'token', period: 'month', limit_value: 0, is_active: true });
    }
    setOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editing) { await api.put(`/api/quotas/${editing.id}`, form); }
      else { await api.post('/api/quotas', form); }
      setOpen(false); fetchQuotas();
      enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) { enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' }); }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(t('common.confirm'))) return;
    try { await api.delete(`/api/quotas/${id}`); fetchQuotas(); } catch {}
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight={600}>{t('quotas.title')}</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => handleOpen()}>{t('quotas.create')}</Button>
      </Box>
      <Card>
        <TableContainer>
          <Table aria-label={t('quotas.title')}>
            <TableHead>
              <TableRow>
                <TableCell>{t('quotas.targetType')}</TableCell>
                <TableCell>{t('quotas.targetId')}</TableCell>
                <TableCell>{t('quotas.quotaType')}</TableCell>
                <TableCell>{t('quotas.period')}</TableCell>
                <TableCell>{t('quotas.limitValue')}</TableCell>
                <TableCell>{t('common.active')}</TableCell>
                <TableCell>{t('common.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {quotas.map((q: any) => (
                <TableRow key={q.id}>
                  <TableCell><Chip label={q.target_type} size="small" /></TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8em' }}>{q.target_id}</TableCell>
                  <TableCell><Chip label={t(`quotas.${q.quota_type}`)} size="small" color={q.quota_type === 'financial' ? 'warning' : 'info'} /></TableCell>
                  <TableCell>{t(`quotas.${q.period}`)}</TableCell>
                  <TableCell>{q.quota_type === 'financial' ? `$${q.limit_value}` : q.limit_value.toLocaleString()}</TableCell>
                  <TableCell><Chip label={q.is_active ? t('common.active') : t('common.inactive')} color={q.is_active ? 'success' : 'default'} size="small" /></TableCell>
                  <TableCell>
                    <IconButton size="small" onClick={() => handleOpen(q)}><Edit /></IconButton>
                    <IconButton size="small" color="error" onClick={() => handleDelete(q.id)}><Delete /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing ? t('quotas.edit') : t('quotas.create')}</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="normal">
            <InputLabel>{t('quotas.targetType')}</InputLabel>
            <Select value={form.target_type} label={t('quotas.targetType')} onChange={e => setForm({ ...form, target_type: e.target.value })}>
              {['user', 'role', 'agent', 'provider'].map(v => <MenuItem key={v} value={v}>{v}</MenuItem>)}
            </Select>
          </FormControl>
          <TextField fullWidth label={t('quotas.targetId')} value={form.target_id} onChange={e => setForm({ ...form, target_id: e.target.value })} margin="normal" required placeholder="UUID" />
          <FormControl fullWidth margin="normal">
            <InputLabel>{t('quotas.quotaType')}</InputLabel>
            <Select value={form.quota_type} label={t('quotas.quotaType')} onChange={e => setForm({ ...form, quota_type: e.target.value })}>
              <MenuItem value="token">{t('quotas.token')}</MenuItem>
              <MenuItem value="financial">{t('quotas.financial')}</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth margin="normal">
            <InputLabel>{t('quotas.period')}</InputLabel>
            <Select value={form.period} label={t('quotas.period')} onChange={e => setForm({ ...form, period: e.target.value })}>
              {['day', 'week', 'month', 'year'].map(v => <MenuItem key={v} value={v}>{t(`quotas.${v}`)}</MenuItem>)}
            </Select>
          </FormControl>
          <TextField fullWidth label={t('quotas.limitValue')} type="number" value={form.limit_value} onChange={e => setForm({ ...form, limit_value: parseFloat(e.target.value) })} margin="normal" required />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={handleSave}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default QuotasPage;
