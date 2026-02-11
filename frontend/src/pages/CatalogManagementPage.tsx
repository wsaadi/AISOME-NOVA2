import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Card, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, IconButton, Chip, FormControl, InputLabel, Select, MenuItem,
  alpha, useTheme, Tooltip,
} from '@mui/material';
import { Add, Edit, Delete, ContentCopy, FileDownload, FileUpload } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

const CatalogManagementPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [agents, setAgents] = useState<any[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [duplicateOpen, setDuplicateOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [selectedAgent, setSelectedAgent] = useState<any>(null);
  const [form, setForm] = useState({ name: '', slug: '', description: '', version: '1.0.0', agent_type: 'conversational', system_prompt: '', config: '{}' });
  const [dupForm, setDupForm] = useState({ new_name: '', new_slug: '' });

  const fetchAgents = useCallback(async () => {
    try { const res = await api.get('/api/agents'); setAgents(res.data); } catch {}
  }, []);

  useEffect(() => { fetchAgents(); }, [fetchAgents]);

  const handleCreate = (agent?: any) => {
    if (agent) {
      setEditing(agent);
      setForm({ name: agent.name, slug: agent.slug, description: agent.description || '', version: agent.version, agent_type: agent.agent_type, system_prompt: agent.system_prompt || '', config: JSON.stringify(agent.config, null, 2) });
    } else {
      setEditing(null);
      setForm({ name: '', slug: '', description: '', version: '1.0.0', agent_type: 'conversational', system_prompt: '', config: '{}' });
    }
    setCreateOpen(true);
  };

  const handleSave = async () => {
    try {
      const data = { ...form, config: JSON.parse(form.config) };
      if (editing) { await api.put(`/api/agents/${editing.id}`, data); }
      else { await api.post('/api/agents', data); }
      setCreateOpen(false); fetchAgents();
      enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) { enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' }); }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(t('agents.confirmDelete'))) return;
    try { await api.delete(`/api/agents/${id}`); fetchAgents(); enqueueSnackbar(t('common.success'), { variant: 'success' }); } catch {}
  };

  const handleDuplicate = async () => {
    if (!selectedAgent) return;
    try {
      await api.post(`/api/agents/${selectedAgent.id}/duplicate?new_name=${encodeURIComponent(dupForm.new_name)}&new_slug=${encodeURIComponent(dupForm.new_slug)}`);
      setDuplicateOpen(false); fetchAgents();
      enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) { enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' }); }
  };

  const handleExport = async (agentId: string) => {
    try {
      const res = await api.post(`/api/agents/${agentId}/export`, null, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `agent_${agentId}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) { enqueueSnackbar(t('common.error'), { variant: 'error' }); }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      await api.post('/api/agents/import', formData);
      fetchAgents();
      enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) { enqueueSnackbar(t('common.error'), { variant: 'error' }); }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 1 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>{t('agents.management')}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {agents.length} agent{agents.length !== 1 ? 's' : ''}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <input type="file" ref={fileInputRef} onChange={handleImport} style={{ display: 'none' }} accept=".zip" />
          <Button variant="outlined" startIcon={<FileUpload />} onClick={() => fileInputRef.current?.click()} sx={{ borderRadius: 2 }}>
            {t('agents.import')}
          </Button>
          <Button variant="contained" startIcon={<Add />} onClick={() => handleCreate()} sx={{ px: 3 }}>
            {t('agents.create')}
          </Button>
        </Box>
      </Box>

      <Card>
        <TableContainer>
          <Table aria-label={t('agents.management')}>
            <TableHead>
              <TableRow>
                <TableCell>{t('agents.name')}</TableCell>
                <TableCell>{t('agents.slug')}</TableCell>
                <TableCell>{t('agents.type')}</TableCell>
                <TableCell>{t('agents.version')}</TableCell>
                <TableCell>{t('common.active')}</TableCell>
                <TableCell align="right">{t('common.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {agents.map((agent: any) => (
                <TableRow key={agent.id} hover>
                  <TableCell><Typography variant="body2" fontWeight={600}>{agent.name}</Typography></TableCell>
                  <TableCell><Chip label={agent.slug} size="small" variant="outlined" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }} /></TableCell>
                  <TableCell><Chip label={agent.agent_type} size="small" color="primary" /></TableCell>
                  <TableCell>{agent.version}</TableCell>
                  <TableCell><Chip label={agent.is_active ? t('common.active') : t('common.inactive')} color={agent.is_active ? 'success' : 'default'} size="small" /></TableCell>
                  <TableCell align="right">
                    <Tooltip title={t('common.edit')}>
                      <IconButton size="small" onClick={() => handleCreate(agent)} sx={{
                        bgcolor: alpha(theme.palette.primary.main, 0.08), mr: 0.5,
                        '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.15) },
                      }}><Edit fontSize="small" /></IconButton>
                    </Tooltip>
                    <Tooltip title={t('agents.duplicate')}>
                      <IconButton size="small" onClick={() => { setSelectedAgent(agent); setDupForm({ new_name: `${agent.name} (copy)`, new_slug: `${agent.slug}-copy` }); setDuplicateOpen(true); }} sx={{
                        bgcolor: alpha(theme.palette.info.main, 0.08), mr: 0.5,
                        '&:hover': { bgcolor: alpha(theme.palette.info.main, 0.15) },
                      }}><ContentCopy fontSize="small" /></IconButton>
                    </Tooltip>
                    <Tooltip title={t('agents.export')}>
                      <IconButton size="small" onClick={() => handleExport(agent.id)} sx={{
                        bgcolor: alpha(theme.palette.success.main, 0.08), mr: 0.5,
                        '&:hover': { bgcolor: alpha(theme.palette.success.main, 0.15) },
                      }}><FileDownload fontSize="small" /></IconButton>
                    </Tooltip>
                    <Tooltip title={t('common.delete')}>
                      <IconButton size="small" color="error" onClick={() => handleDelete(agent.id)} sx={{
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

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editing ? t('agents.edit') : t('agents.create')}</DialogTitle>
        <DialogContent>
          <TextField fullWidth label={t('agents.name')} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} margin="normal" required />
          <TextField fullWidth label={t('agents.slug')} value={form.slug} onChange={e => setForm({ ...form, slug: e.target.value })} margin="normal" required disabled={!!editing} />
          <TextField fullWidth label={t('agents.description')} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} margin="normal" multiline rows={2} />
          <TextField fullWidth label={t('agents.version')} value={form.version} onChange={e => setForm({ ...form, version: e.target.value })} margin="normal" />
          <FormControl fullWidth margin="normal">
            <InputLabel>{t('agents.type')}</InputLabel>
            <Select value={form.agent_type} label={t('agents.type')} onChange={e => setForm({ ...form, agent_type: e.target.value })}>
              <MenuItem value="conversational">{t('agents.conversational')}</MenuItem>
              <MenuItem value="rag">{t('agents.rag')}</MenuItem>
              <MenuItem value="workflow">{t('agents.workflow')}</MenuItem>
              <MenuItem value="custom">{t('agents.custom')}</MenuItem>
            </Select>
          </FormControl>
          <TextField fullWidth label={t('agents.systemPrompt')} value={form.system_prompt} onChange={e => setForm({ ...form, system_prompt: e.target.value })} margin="normal" multiline rows={4} />
          <TextField fullWidth label={t('agents.config')} value={form.config} onChange={e => setForm({ ...form, config: e.target.value })} margin="normal" multiline rows={4} sx={{ '& textarea': { fontFamily: 'monospace' } }} />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setCreateOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={handleSave}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={duplicateOpen} onClose={() => setDuplicateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('agents.duplicate')}: {selectedAgent?.name}</DialogTitle>
        <DialogContent>
          <TextField fullWidth label={t('agents.newName')} value={dupForm.new_name} onChange={e => setDupForm({ ...dupForm, new_name: e.target.value })} margin="normal" required />
          <TextField fullWidth label={t('agents.newSlug')} value={dupForm.new_slug} onChange={e => setDupForm({ ...dupForm, new_slug: e.target.value })} margin="normal" required />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setDuplicateOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={handleDuplicate}>{t('agents.duplicate')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CatalogManagementPage;
