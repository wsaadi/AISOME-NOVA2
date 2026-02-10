import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Card, CardContent, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, IconButton, FormControl, InputLabel, Select,
  MenuItem, Chip, Alert, alpha, useTheme, Tooltip,
} from '@mui/material';
import { Add, Edit, Delete, PlayArrow } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

const ENTITY_TYPES = ['person', 'email', 'phone', 'address', 'credit_card', 'ssn', 'date_of_birth', 'ip_address', 'organization', 'location'];

const ModerationPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const [rules, setRules] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState({ name: '', agent_id: '', rule_type: 'anonymization', entity_types: [] as string[], action: 'redact', replacement_template: '[REDACTED]', is_active: true });
  const [testText, setTestText] = useState('');
  const [testResult, setTestResult] = useState<any>(null);

  const fetchRules = useCallback(async () => {
    try { const res = await api.get('/api/moderation/rules'); setRules(res.data); } catch {}
  }, []);

  useEffect(() => { fetchRules(); }, [fetchRules]);

  const handleOpen = (rule?: any) => {
    if (rule) {
      setEditing(rule);
      setForm({ name: rule.name, agent_id: rule.agent_id || '', rule_type: rule.rule_type, entity_types: rule.entity_types, action: rule.action, replacement_template: rule.replacement_template || '[REDACTED]', is_active: rule.is_active });
    } else {
      setEditing(null);
      setForm({ name: '', agent_id: '', rule_type: 'anonymization', entity_types: [], action: 'redact', replacement_template: '[REDACTED]', is_active: true });
    }
    setOpen(true);
  };

  const handleSave = async () => {
    try {
      const data = { ...form, agent_id: form.agent_id || null };
      if (editing) { await api.put(`/api/moderation/rules/${editing.id}`, data); }
      else { await api.post('/api/moderation/rules', data); }
      setOpen(false); fetchRules();
      enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) { enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' }); }
  };

  const handleDelete = async (id: string) => {
    try { await api.delete(`/api/moderation/rules/${id}`); fetchRules(); } catch {}
  };

  const handleTest = async () => {
    try {
      const res = await api.post('/api/moderation/test', { text: testText, entity_types: ENTITY_TYPES });
      setTestResult(res.data);
    } catch { setTestResult(null); }
  };

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} gutterBottom>{t('moderation.title')}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>{t('app.subtitle')}</Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight={600}>{t('moderation.testModeration')}</Typography>
          <TextField fullWidth multiline rows={3} label={t('moderation.testInput')} value={testText} onChange={e => setTestText(e.target.value)} sx={{ mb: 2 }} />
          <Button variant="outlined" startIcon={<PlayArrow />} onClick={handleTest} sx={{ borderRadius: 2 }}>
            {t('moderation.testModeration')}
          </Button>
          {testResult && (
            <Box sx={{ mt: 2 }}>
              <Alert severity="info" sx={{ mb: 1, borderRadius: 2 }}><strong>{t('moderation.testResult')}:</strong> {testResult.redacted}</Alert>
              {testResult.entities?.length > 0 && (
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {testResult.entities.map((e: any, i: number) => (
                    <Chip key={i} label={`${e.label}: ${e.text}`} color="warning" size="small" />
                  ))}
                </Box>
              )}
            </Box>
          )}
        </CardContent>
      </Card>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" fontWeight={600}>{t('moderation.rules')}</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => handleOpen()} sx={{ px: 3 }}>
          {t('moderation.createRule')}
        </Button>
      </Box>

      <Card>
        <TableContainer>
          <Table aria-label={t('moderation.rules')}>
            <TableHead>
              <TableRow>
                <TableCell>{t('moderation.ruleName')}</TableCell>
                <TableCell>{t('moderation.ruleType')}</TableCell>
                <TableCell>{t('moderation.entityTypes')}</TableCell>
                <TableCell>{t('moderation.action')}</TableCell>
                <TableCell>{t('common.active')}</TableCell>
                <TableCell align="right">{t('common.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rules.map((rule: any) => (
                <TableRow key={rule.id} hover>
                  <TableCell><Typography variant="body2" fontWeight={500}>{rule.name}</Typography></TableCell>
                  <TableCell><Chip label={rule.rule_type} size="small" color="primary" /></TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {rule.entity_types?.slice(0, 3).map((et: string) => <Chip key={et} label={et} size="small" variant="outlined" sx={{ height: 24, fontSize: '0.7rem' }} />)}
                      {rule.entity_types?.length > 3 && <Chip label={`+${rule.entity_types.length - 3}`} size="small" sx={{ height: 24, fontSize: '0.7rem' }} />}
                    </Box>
                  </TableCell>
                  <TableCell><Chip label={t(`moderation.${rule.action}`)} size="small" color={rule.action === 'block' ? 'error' : rule.action === 'redact' ? 'warning' : 'info'} /></TableCell>
                  <TableCell><Chip label={rule.is_active ? t('common.active') : t('common.inactive')} color={rule.is_active ? 'success' : 'default'} size="small" /></TableCell>
                  <TableCell align="right">
                    <Tooltip title={t('common.edit')}>
                      <IconButton size="small" onClick={() => handleOpen(rule)} sx={{
                        bgcolor: alpha(theme.palette.primary.main, 0.08), mr: 0.5,
                        '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.15) },
                      }}><Edit fontSize="small" /></IconButton>
                    </Tooltip>
                    <Tooltip title={t('common.delete')}>
                      <IconButton size="small" color="error" onClick={() => handleDelete(rule.id)} sx={{
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
        <DialogTitle>{editing ? t('moderation.editRule') : t('moderation.createRule')}</DialogTitle>
        <DialogContent>
          <TextField fullWidth label={t('moderation.ruleName')} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} margin="normal" required />
          <FormControl fullWidth margin="normal">
            <InputLabel>{t('moderation.ruleType')}</InputLabel>
            <Select value={form.rule_type} label={t('moderation.ruleType')} onChange={e => setForm({ ...form, rule_type: e.target.value })}>
              <MenuItem value="anonymization">{t('moderation.anonymization')}</MenuItem>
              <MenuItem value="content_filter">{t('moderation.contentFilter')}</MenuItem>
              <MenuItem value="pii_detection">{t('moderation.piiDetection')}</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth margin="normal">
            <InputLabel>{t('moderation.entityTypes')}</InputLabel>
            <Select multiple value={form.entity_types} label={t('moderation.entityTypes')} onChange={e => setForm({ ...form, entity_types: e.target.value as string[] })} renderValue={(selected) => selected.join(', ')}>
              {ENTITY_TYPES.map(et => <MenuItem key={et} value={et}>{et}</MenuItem>)}
            </Select>
          </FormControl>
          <FormControl fullWidth margin="normal">
            <InputLabel>{t('moderation.action')}</InputLabel>
            <Select value={form.action} label={t('moderation.action')} onChange={e => setForm({ ...form, action: e.target.value })}>
              <MenuItem value="redact">{t('moderation.redact')}</MenuItem>
              <MenuItem value="block">{t('moderation.block')}</MenuItem>
              <MenuItem value="flag">{t('moderation.flag')}</MenuItem>
              <MenuItem value="replace">{t('moderation.replace')}</MenuItem>
            </Select>
          </FormControl>
          <TextField fullWidth label={t('moderation.replacement')} value={form.replacement_template} onChange={e => setForm({ ...form, replacement_template: e.target.value })} margin="normal" />
          <TextField fullWidth label="Agent ID (optional)" value={form.agent_id} onChange={e => setForm({ ...form, agent_id: e.target.value })} margin="normal" placeholder="Leave empty for global rule" />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={handleSave}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ModerationPage;
