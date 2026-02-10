import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Card, CardContent, IconButton, Checkbox, FormControlLabel, Accordion,
  AccordionSummary, AccordionDetails, Grid, Chip, alpha, useTheme, Avatar, Tooltip,
} from '@mui/material';
import { Add, Edit, Delete, ExpandMore, Security, AdminPanelSettings, VisibilityOutlined } from '@mui/icons-material';
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

const ROLE_COLORS = [
  { gradient: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)' },
  { gradient: 'linear-gradient(135deg, #059669 0%, #10B981 100%)' },
  { gradient: 'linear-gradient(135deg, #D97706 0%, #F59E0B 100%)' },
  { gradient: 'linear-gradient(135deg, #DC2626 0%, #EF4444 100%)' },
  { gradient: 'linear-gradient(135deg, #7C3AED 0%, #EC4899 100%)' },
];

const ROLE_ICONS = [<AdminPanelSettings />, <Security />, <VisibilityOutlined />];

interface Role { id: string; name: string; description: string | null; permissions: Record<string, Record<string, boolean>>; }

const RolesPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const [roles, setRoles] = useState<Role[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Role | null>(null);
  const [form, setForm] = useState({ name: '', description: '', permissions: {} as Record<string, Record<string, boolean>> });

  const fetchRoles = useCallback(async () => {
    try { const res = await api.get('/api/roles'); setRoles(res.data); } catch {}
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
      if (editing) { await api.put(`/api/roles/${editing.id}`, form); }
      else { await api.post('/api/roles', form); }
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

  const countPermissions = (perms: Record<string, Record<string, boolean>>) => {
    if (!perms) return 0;
    return Object.values(perms).reduce((count, resource) =>
      count + Object.values(resource).filter(Boolean).length, 0);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>{t('roles.title')}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {roles.length} {t('roles.title').toLowerCase()}
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<Add />} onClick={() => handleOpen()} sx={{ px: 3 }}>
          {t('roles.create')}
        </Button>
      </Box>

      <Grid container spacing={3}>
        {roles.map((role, index) => {
          const colorSet = ROLE_COLORS[index % ROLE_COLORS.length];
          const permCount = countPermissions(role.permissions);
          return (
            <Grid item xs={12} sm={6} md={4} key={role.id}>
              <Card sx={{
                height: '100%', position: 'relative', overflow: 'hidden',
                '&:hover': { transform: 'translateY(-2px)' },
                transition: 'all 0.2s ease',
              }}>
                <Box sx={{ height: 4, background: colorSet.gradient }} />
                <CardContent sx={{ pt: 2.5, pb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Avatar variant="rounded" sx={{
                        width: 44, height: 44, background: colorSet.gradient, borderRadius: '12px',
                      }}>
                        {ROLE_ICONS[index % ROLE_ICONS.length]}
                      </Avatar>
                      <Box>
                        <Typography variant="subtitle1" fontWeight={700} color="text.primary">
                          {role.name}
                        </Typography>
                        <Chip label={`${permCount} permissions`} size="small" color="primary" sx={{ height: 22, fontSize: '0.7rem', mt: 0.25 }} />
                      </Box>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      <Tooltip title={t('common.edit')}>
                        <IconButton size="small" onClick={() => handleOpen(role)} sx={{
                          bgcolor: alpha(theme.palette.primary.main, 0.08),
                          '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.15) },
                        }}>
                          <Edit fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={t('common.delete')}>
                        <IconButton size="small" onClick={() => handleDelete(role.id)} sx={{
                          bgcolor: alpha(theme.palette.error.main, 0.08),
                          '&:hover': { bgcolor: alpha(theme.palette.error.main, 0.15) },
                          color: 'error.main',
                        }}>
                          <Delete fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>
                  {role.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2, lineHeight: 1.6 }}>
                      {role.description}
                    </Typography>
                  )}
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {role.permissions && Object.entries(role.permissions)
                      .filter(([_, actions]) => Object.values(actions).some(Boolean))
                      .slice(0, 5)
                      .map(([key]) => (
                        <Chip key={key} label={key.replace('_', '-')} size="small" variant="outlined" sx={{ height: 24, fontSize: '0.7rem' }} />
                      ))}
                    {role.permissions && Object.entries(role.permissions)
                      .filter(([_, actions]) => Object.values(actions).some(Boolean)).length > 5 && (
                      <Chip
                        label={`+${Object.entries(role.permissions).filter(([_, actions]) => Object.values(actions).some(Boolean)).length - 5}`}
                        size="small" sx={{ height: 24, fontSize: '0.7rem' }}
                      />
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editing ? t('roles.edit') : t('roles.create')}</DialogTitle>
        <DialogContent>
          <TextField fullWidth label={t('roles.name')} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} margin="normal" required />
          <TextField fullWidth label={t('roles.description')} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} margin="normal" multiline rows={2} />
          <Typography variant="h6" sx={{ mt: 3, mb: 1.5 }}>{t('roles.permissions')}</Typography>
          {PERMISSION_RESOURCES.map(resource => (
            <Accordion key={resource.key} disableGutters sx={{ mb: 1 }}>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography fontWeight={500} sx={{ textTransform: 'capitalize' }}>{resource.key.replace('_', ' ')}</Typography>
                  <Chip
                    label={resource.actions.filter(a => form.permissions[resource.key]?.[a]).length + '/' + resource.actions.length}
                    size="small"
                    color={resource.actions.filter(a => form.permissions[resource.key]?.[a]).length > 0 ? 'primary' : 'default'}
                    sx={{ height: 22, fontSize: '0.7rem' }}
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={1}>
                  {resource.actions.map(action => (
                    <Grid item xs={6} sm={4} key={action}>
                      <FormControlLabel
                        control={<Checkbox checked={form.permissions[resource.key]?.[action] || false} onChange={() => togglePerm(resource.key, action)} />}
                        label={<Typography variant="body2" sx={{ textTransform: 'capitalize' }}>{action}</Typography>}
                      />
                    </Grid>
                  ))}
                </Grid>
              </AccordionDetails>
            </Accordion>
          ))}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={handleSave}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RolesPage;
