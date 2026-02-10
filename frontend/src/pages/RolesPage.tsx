import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Card, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, IconButton, Checkbox, FormControlLabel, Accordion, AccordionSummary,
  AccordionDetails, Grid,
} from '@mui/material';
import { Add, Edit, Delete, ExpandMore } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

const PERMISSION_RESOURCES = [
  { key: 'users', actions: ['read', 'write', 'delete'] },
  { key: 'roles', actions: ['read', 'write', 'delete'] },
  { key: 'llm_config', actions: ['read', 'write'] },
  { key: 'consumption', actions: ['read'] },
  { key: 'quotas', actions: ['read', 'write'] },
  { key: 'costs', actions: ['read', 'write'] },
  { key: 'moderation', actions: ['read', 'write'] },
  { key: 'agents', actions: ['read', 'write', 'delete', 'export', 'import'] },
  { key: 'catalog_management', actions: ['read', 'write'] },
  { key: 'system', actions: ['read', 'update'] },
];

interface Role { id: string; name: string; description: string | null; permissions: Record<string, Record<string, boolean>>; }

const RolesPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const [roles, setRoles] = useState<Role[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Role | null>(null);
  const [form, setForm] = useState({ name: '', description: '', permissions: {} as Record<string, Record<string, boolean>> });

  const fetchRoles = useCallback(async () => {
    try {
      const res = await api.get('/api/roles');
      setRoles(res.data);
    } catch {}
  }, []);

  useEffect(() => { fetchRoles(); }, [fetchRoles]);

  const handleOpen = (role?: Role) => {
    if (role) {
      setEditing(role);
      setForm({ name: role.name, description: role.description || '', permissions: role.permissions || {} });
    } else {
      setEditing(null);
      const defaultPerms: any = {};
      PERMISSION_RESOURCES.forEach(r => { defaultPerms[r.key] = {}; r.actions.forEach(a => defaultPerms[r.key][a] = false); });
      setForm({ name: '', description: '', permissions: defaultPerms });
    }
    setOpen(true);
  };

  const togglePerm = (resource: string, action: string) => {
    setForm(prev => ({
      ...prev,
      permissions: {
        ...prev.permissions,
        [resource]: { ...prev.permissions[resource], [action]: !prev.permissions[resource]?.[action] }
      }
    }));
  };

  const handleSave = async () => {
    try {
      if (editing) {
        await api.put(`/api/roles/${editing.id}`, form);
      } else {
        await api.post('/api/roles', form);
      }
      setOpen(false);
      fetchRoles();
      enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) {
      enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' });
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(t('roles.confirmDelete'))) return;
    try {
      await api.delete(`/api/roles/${id}`);
      fetchRoles();
      enqueueSnackbar(t('common.success'), { variant: 'success' });
    } catch (e: any) {
      enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' });
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight={600}>{t('roles.title')}</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => handleOpen()}>{t('roles.create')}</Button>
      </Box>
      <Card>
        <TableContainer>
          <Table aria-label={t('roles.title')}>
            <TableHead>
              <TableRow>
                <TableCell>{t('roles.name')}</TableCell>
                <TableCell>{t('roles.description')}</TableCell>
                <TableCell>{t('common.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {roles.map(role => (
                <TableRow key={role.id}>
                  <TableCell>{role.name}</TableCell>
                  <TableCell>{role.description}</TableCell>
                  <TableCell>
                    <IconButton size="small" onClick={() => handleOpen(role)} aria-label={t('common.edit')}><Edit /></IconButton>
                    <IconButton size="small" onClick={() => handleDelete(role.id)} color="error" aria-label={t('common.delete')}><Delete /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editing ? t('roles.edit') : t('roles.create')}</DialogTitle>
        <DialogContent>
          <TextField fullWidth label={t('roles.name')} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} margin="normal" required />
          <TextField fullWidth label={t('roles.description')} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} margin="normal" multiline rows={2} />
          <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>{t('roles.permissions')}</Typography>
          {PERMISSION_RESOURCES.map(resource => (
            <Accordion key={resource.key} disableGutters>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography fontWeight={500}>{resource.key}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={1}>
                  {resource.actions.map(action => (
                    <Grid item xs={6} sm={4} key={action}>
                      <FormControlLabel
                        control={<Checkbox checked={form.permissions[resource.key]?.[action] || false} onChange={() => togglePerm(resource.key, action)} />}
                        label={action}
                      />
                    </Grid>
                  ))}
                </Grid>
              </AccordionDetails>
            </Accordion>
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={handleSave}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RolesPage;
