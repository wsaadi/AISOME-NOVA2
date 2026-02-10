import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Card, CardContent, Grid, FormControl, InputLabel,
  Select, MenuItem, TextField, ToggleButton, ToggleButtonGroup, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow, alpha, useTheme,
  Tabs, Tab, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  IconButton, Chip, Tooltip,
} from '@mui/material';
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area, PieChart, Pie,
  Cell, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { Add, Edit, Delete } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

const COLORS = ['#4F46E5', '#7C3AED', '#10B981', '#F59E0B', '#EF4444', '#3B82F6', '#EC4899', '#14B8A6'];

/* ── Consumption Tab ── */
const ConsumptionTab: React.FC = () => {
  const { t } = useTranslation();
  const theme = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [rawData, setRawData] = useState<any[]>([]);
  const [groupBy, setGroupBy] = useState('day');
  const [chartType, setChartType] = useState('bar');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const fetchData = useCallback(async () => {
    try {
      const params: any = { group_by: groupBy };
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const [summaryRes, rawRes] = await Promise.all([
        api.get('/api/consumption/summary', { params }),
        api.get('/api/consumption', { params: { date_from: dateFrom || undefined, date_to: dateTo || undefined, limit: 100 } }),
      ]);
      setData(summaryRes.data);
      setRawData(rawRes.data);
    } catch {}
  }, [groupBy, dateFrom, dateTo]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const chartData = data.map(d => ({
    name: d.group_value,
    tokens_in: d.total_tokens_in,
    tokens_out: d.total_tokens_out,
    cost: (d.total_cost_in + d.total_cost_out).toFixed(4),
  }));

  const renderChart = () => {
    if (!chartData.length) return (
      <Box sx={{ py: 8, textAlign: 'center' }}>
        <Typography color="text.secondary">{t('common.noData')}</Typography>
      </Box>
    );
    switch (chartType) {
      case 'line':
        return <ResponsiveContainer width="100%" height={350}><LineChart data={chartData}><CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} /><XAxis dataKey="name" /><YAxis /><RTooltip /><Legend /><Line type="monotone" dataKey="tokens_in" stroke="#4F46E5" strokeWidth={2} name={t('consumption.tokensIn')} /><Line type="monotone" dataKey="tokens_out" stroke="#7C3AED" strokeWidth={2} name={t('consumption.tokensOut')} /></LineChart></ResponsiveContainer>;
      case 'area':
        return <ResponsiveContainer width="100%" height={350}><AreaChart data={chartData}><CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} /><XAxis dataKey="name" /><YAxis /><RTooltip /><Legend /><Area type="monotone" dataKey="tokens_in" stroke="#4F46E5" fill={alpha('#4F46E5', 0.15)} name={t('consumption.tokensIn')} /><Area type="monotone" dataKey="tokens_out" stroke="#7C3AED" fill={alpha('#7C3AED', 0.15)} name={t('consumption.tokensOut')} /></AreaChart></ResponsiveContainer>;
      case 'pie':
      case 'donut':
        const pieData = chartData.map((d) => ({ name: d.name, value: d.tokens_in + d.tokens_out }));
        return <ResponsiveContainer width="100%" height={350}><PieChart><Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={120} innerRadius={chartType === 'donut' ? 60 : 0} label>{pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><RTooltip /><Legend /></PieChart></ResponsiveContainer>;
      default:
        return <ResponsiveContainer width="100%" height={350}><BarChart data={chartData}><CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} /><XAxis dataKey="name" /><YAxis /><RTooltip /><Legend /><Bar dataKey="tokens_in" fill="#4F46E5" radius={[4, 4, 0, 0]} name={t('consumption.tokensIn')} /><Bar dataKey="tokens_out" fill="#7C3AED" radius={[4, 4, 0, 0]} name={t('consumption.tokensOut')} /></BarChart></ResponsiveContainer>;
    }
  };

  return (
    <Box>
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 2.5 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={3}>
              <TextField fullWidth type="date" label={t('consumption.dateFrom')} value={dateFrom} onChange={e => setDateFrom(e.target.value)} InputLabelProps={{ shrink: true }} size="small" />
            </Grid>
            <Grid item xs={12} sm={3}>
              <TextField fullWidth type="date" label={t('consumption.dateTo')} value={dateTo} onChange={e => setDateTo(e.target.value)} InputLabelProps={{ shrink: true }} size="small" />
            </Grid>
            <Grid item xs={12} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>{t('consumption.groupBy')}</InputLabel>
                <Select value={groupBy} label={t('consumption.groupBy')} onChange={e => setGroupBy(e.target.value)}>
                  <MenuItem value="day">{t('consumption.day')}</MenuItem>
                  <MenuItem value="user">{t('consumption.user')}</MenuItem>
                  <MenuItem value="agent">{t('consumption.agent')}</MenuItem>
                  <MenuItem value="provider">{t('consumption.provider')}</MenuItem>
                  <MenuItem value="model">{t('consumption.model')}</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={3}>
              <ToggleButtonGroup value={chartType} exclusive onChange={(_, v) => v && setChartType(v)} size="small" fullWidth
                sx={{ '& .MuiToggleButton-root': { borderRadius: 2, textTransform: 'none', fontWeight: 500, fontSize: '0.8rem' } }}>
                <ToggleButton value="bar">{t('consumption.bar')}</ToggleButton>
                <ToggleButton value="line">{t('consumption.line')}</ToggleButton>
                <ToggleButton value="area">{t('consumption.area')}</ToggleButton>
                <ToggleButton value="pie">{t('consumption.pie')}</ToggleButton>
              </ToggleButtonGroup>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>{renderChart()}</CardContent>
      </Card>
      <Card>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t('consumption.tokensIn')}</TableCell>
                <TableCell>{t('consumption.tokensOut')}</TableCell>
                <TableCell>{t('consumption.costIn')}</TableCell>
                <TableCell>{t('consumption.costOut')}</TableCell>
                <TableCell>Date</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rawData.map((row: any) => (
                <TableRow key={row.id} hover>
                  <TableCell>{row.tokens_in?.toLocaleString()}</TableCell>
                  <TableCell>{row.tokens_out?.toLocaleString()}</TableCell>
                  <TableCell sx={{ fontFamily: 'monospace' }}>${row.cost_in?.toFixed(6)}</TableCell>
                  <TableCell sx={{ fontFamily: 'monospace' }}>${row.cost_out?.toFixed(6)}</TableCell>
                  <TableCell>{new Date(row.created_at).toLocaleString()}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>
    </Box>
  );
};

/* ── Quotas Tab ── */
const QuotasTab: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const [quotas, setQuotas] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState({ target_type: 'user', target_id: '', quota_type: 'token', period: 'month', limit_value: 0, is_active: true });

  const fetchQuotas = useCallback(async () => {
    try { const res = await api.get('/api/quotas'); setQuotas(res.data); } catch {}
  }, []);
  useEffect(() => { fetchQuotas(); }, [fetchQuotas]);

  const handleOpen = (q?: any) => {
    if (q) { setEditing(q); setForm({ target_type: q.target_type, target_id: q.target_id, quota_type: q.quota_type, period: q.period, limit_value: q.limit_value, is_active: q.is_active }); }
    else { setEditing(null); setForm({ target_type: 'user', target_id: '', quota_type: 'token', period: 'month', limit_value: 0, is_active: true }); }
    setOpen(true);
  };
  const handleSave = async () => {
    try {
      if (editing) { await api.put(`/api/quotas/${editing.id}`, form); } else { await api.post('/api/quotas', form); }
      setOpen(false); fetchQuotas(); enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) { enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' }); }
  };
  const handleDelete = async (id: string) => {
    if (!window.confirm(t('common.confirm'))) return;
    try { await api.delete(`/api/quotas/${id}`); fetchQuotas(); } catch {}
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
        <Button variant="contained" startIcon={<Add />} onClick={() => handleOpen()} sx={{ px: 3 }}>{t('quotas.create')}</Button>
      </Box>
      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t('quotas.targetType')}</TableCell>
                <TableCell>{t('quotas.targetId')}</TableCell>
                <TableCell>{t('quotas.quotaType')}</TableCell>
                <TableCell>{t('quotas.period')}</TableCell>
                <TableCell>{t('quotas.limitValue')}</TableCell>
                <TableCell>{t('common.active')}</TableCell>
                <TableCell align="right">{t('common.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {quotas.map((q: any) => (
                <TableRow key={q.id} hover>
                  <TableCell><Chip label={q.target_type} size="small" color="primary" /></TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8em' }}>{q.target_id}</TableCell>
                  <TableCell><Chip label={t(`quotas.${q.quota_type}`)} size="small" color={q.quota_type === 'financial' ? 'warning' : 'info'} /></TableCell>
                  <TableCell>{t(`quotas.${q.period}`)}</TableCell>
                  <TableCell><Typography variant="body2" fontWeight={600}>{q.quota_type === 'financial' ? `$${q.limit_value}` : q.limit_value.toLocaleString()}</Typography></TableCell>
                  <TableCell><Chip label={q.is_active ? t('common.active') : t('common.inactive')} color={q.is_active ? 'success' : 'default'} size="small" /></TableCell>
                  <TableCell align="right">
                    <Tooltip title={t('common.edit')}><IconButton size="small" onClick={() => handleOpen(q)} sx={{ bgcolor: alpha(theme.palette.primary.main, 0.08), mr: 0.5, '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.15) } }}><Edit fontSize="small" /></IconButton></Tooltip>
                    <Tooltip title={t('common.delete')}><IconButton size="small" color="error" onClick={() => handleDelete(q.id)} sx={{ bgcolor: alpha(theme.palette.error.main, 0.08), '&:hover': { bgcolor: alpha(theme.palette.error.main, 0.15) } }}><Delete fontSize="small" /></IconButton></Tooltip>
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
          <FormControl fullWidth margin="normal"><InputLabel>{t('quotas.targetType')}</InputLabel><Select value={form.target_type} label={t('quotas.targetType')} onChange={e => setForm({ ...form, target_type: e.target.value })}>{['user', 'role', 'agent', 'provider'].map(v => <MenuItem key={v} value={v}>{v}</MenuItem>)}</Select></FormControl>
          <TextField fullWidth label={t('quotas.targetId')} value={form.target_id} onChange={e => setForm({ ...form, target_id: e.target.value })} margin="normal" required placeholder="UUID" />
          <FormControl fullWidth margin="normal"><InputLabel>{t('quotas.quotaType')}</InputLabel><Select value={form.quota_type} label={t('quotas.quotaType')} onChange={e => setForm({ ...form, quota_type: e.target.value })}><MenuItem value="token">{t('quotas.token')}</MenuItem><MenuItem value="financial">{t('quotas.financial')}</MenuItem></Select></FormControl>
          <FormControl fullWidth margin="normal"><InputLabel>{t('quotas.period')}</InputLabel><Select value={form.period} label={t('quotas.period')} onChange={e => setForm({ ...form, period: e.target.value })}>{['day', 'week', 'month', 'year'].map(v => <MenuItem key={v} value={v}>{t(`quotas.${v}`)}</MenuItem>)}</Select></FormControl>
          <TextField fullWidth label={t('quotas.limitValue')} type="number" value={form.limit_value} onChange={e => setForm({ ...form, limit_value: parseFloat(e.target.value) })} margin="normal" required />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}><Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button><Button variant="contained" onClick={handleSave}>{t('common.save')}</Button></DialogActions>
      </Dialog>
    </Box>
  );
};

/* ── Costs Tab ── */
const CostsTab: React.FC = () => {
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

  const handleOpen = (c?: any) => {
    if (c) { setEditing(c); setForm({ model_id: c.model_id, cost_per_token_in: c.cost_per_token_in, cost_per_token_out: c.cost_per_token_out, effective_date: c.effective_date }); }
    else { setEditing(null); setForm({ model_id: '', cost_per_token_in: 0, cost_per_token_out: 0, effective_date: new Date().toISOString().split('T')[0] }); }
    setOpen(true);
  };
  const handleSave = async () => {
    try {
      if (editing) { await api.put(`/api/costs/${editing.id}`, form); } else { await api.post('/api/costs', form); }
      setOpen(false); fetchCosts(); enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) { enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' }); }
  };
  const handleDelete = async (id: string) => {
    try { await api.delete(`/api/costs/${id}`); fetchCosts(); } catch {}
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
        <Button variant="contained" startIcon={<Add />} onClick={() => handleOpen()} sx={{ px: 3 }}>{t('costs.create')}</Button>
      </Box>
      <Card>
        <TableContainer>
          <Table>
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
                    <Tooltip title={t('common.edit')}><IconButton size="small" onClick={() => handleOpen(c)} sx={{ bgcolor: alpha(theme.palette.primary.main, 0.08), mr: 0.5, '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.15) } }}><Edit fontSize="small" /></IconButton></Tooltip>
                    <Tooltip title={t('common.delete')}><IconButton size="small" color="error" onClick={() => handleDelete(c.id)} sx={{ bgcolor: alpha(theme.palette.error.main, 0.08), '&:hover': { bgcolor: alpha(theme.palette.error.main, 0.15) } }}><Delete fontSize="small" /></IconButton></Tooltip>
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
        <DialogActions sx={{ px: 3, pb: 2.5 }}><Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button><Button variant="contained" onClick={handleSave}>{t('common.save')}</Button></DialogActions>
      </Dialog>
    </Box>
  );
};

/* ── Main Page with Tabs ── */
const ConsumptionPage: React.FC = () => {
  const { t } = useTranslation();
  const theme = useTheme();
  const [tab, setTab] = useState(0);

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} gutterBottom>{t('consumption.title')}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{t('app.subtitle')}</Typography>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}
          sx={{
            '& .MuiTab-root': { textTransform: 'none', fontWeight: 600, fontSize: '0.9rem', minHeight: 48 },
            '& .MuiTabs-indicator': { height: 3, borderRadius: '3px 3px 0 0' },
          }}>
          <Tab label={t('consumption.title')} />
          <Tab label={t('quotas.title')} />
          <Tab label={t('costs.title')} />
        </Tabs>
      </Box>

      {tab === 0 && <ConsumptionTab />}
      {tab === 1 && <QuotasTab />}
      {tab === 2 && <CostsTab />}
    </Box>
  );
};

export default ConsumptionPage;
