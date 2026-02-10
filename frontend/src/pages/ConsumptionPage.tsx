import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Card, CardContent, Grid, FormControl, InputLabel,
  Select, MenuItem, TextField, ToggleButton, ToggleButtonGroup, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow,
} from '@mui/material';
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area, PieChart, Pie,
  Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import api from '../services/api';

const COLORS = ['#1976d2', '#9c27b0', '#2e7d32', '#ed6c02', '#d32f2f', '#0288d1', '#f44336', '#4caf50'];

const ConsumptionPage: React.FC = () => {
  const { t } = useTranslation();
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
    if (!chartData.length) return <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>{t('common.noData')}</Typography>;
    switch (chartType) {
      case 'line':
        return <ResponsiveContainer width="100%" height={350}><LineChart data={chartData}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip /><Legend /><Line type="monotone" dataKey="tokens_in" stroke="#1976d2" name={t('consumption.tokensIn')} /><Line type="monotone" dataKey="tokens_out" stroke="#9c27b0" name={t('consumption.tokensOut')} /></LineChart></ResponsiveContainer>;
      case 'area':
        return <ResponsiveContainer width="100%" height={350}><AreaChart data={chartData}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip /><Legend /><Area type="monotone" dataKey="tokens_in" stroke="#1976d2" fill="#1976d220" name={t('consumption.tokensIn')} /><Area type="monotone" dataKey="tokens_out" stroke="#9c27b0" fill="#9c27b020" name={t('consumption.tokensOut')} /></AreaChart></ResponsiveContainer>;
      case 'pie':
      case 'donut':
        const pieData = chartData.map((d, i) => ({ name: d.name, value: d.tokens_in + d.tokens_out }));
        return <ResponsiveContainer width="100%" height={350}><PieChart><Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={120} innerRadius={chartType === 'donut' ? 60 : 0} label>{pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart></ResponsiveContainer>;
      default:
        return <ResponsiveContainer width="100%" height={350}><BarChart data={chartData}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip /><Legend /><Bar dataKey="tokens_in" fill="#1976d2" name={t('consumption.tokensIn')} /><Bar dataKey="tokens_out" fill="#9c27b0" name={t('consumption.tokensOut')} /></BarChart></ResponsiveContainer>;
    }
  };

  return (
    <Box>
      <Typography variant="h4" fontWeight={600} gutterBottom>{t('consumption.title')}</Typography>
      <Card sx={{ mb: 3 }}>
        <CardContent>
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
              <ToggleButtonGroup value={chartType} exclusive onChange={(_, v) => v && setChartType(v)} size="small" fullWidth>
                <ToggleButton value="bar">{t('consumption.bar')}</ToggleButton>
                <ToggleButton value="line">{t('consumption.line')}</ToggleButton>
                <ToggleButton value="area">{t('consumption.area')}</ToggleButton>
                <ToggleButton value="pie">{t('consumption.pie')}</ToggleButton>
                <ToggleButton value="donut">{t('consumption.donut')}</ToggleButton>
              </ToggleButtonGroup>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
      <Card sx={{ mb: 3 }}>
        <CardContent>{renderChart()}</CardContent>
      </Card>
      <Card>
        <TableContainer>
          <Table size="small" aria-label={t('consumption.title')}>
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
                <TableRow key={row.id}>
                  <TableCell>{row.tokens_in}</TableCell>
                  <TableCell>{row.tokens_out}</TableCell>
                  <TableCell>${row.cost_in?.toFixed(6)}</TableCell>
                  <TableCell>${row.cost_out?.toFixed(6)}</TableCell>
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

export default ConsumptionPage;
