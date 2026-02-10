import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Switch, FormControlLabel, IconButton, Chip, Card, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow, Select,
  MenuItem, FormControl, InputLabel, OutlinedInput,
} from '@mui/material';
import { Add, Edit, Delete } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

interface User {
  id: string; email: string; username: string; first_name: string | null;
  last_name: string | null; is_active: boolean; roles: { id: string; name: string }[];
  preferred_language: string;
}
interface Role { id: string; name: string; }

const UsersPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [form, setForm] = useState({ email: '', username: '', password: '', first_name: '', last_name: '', is_active: true, preferred_language: 'en', role_ids: [] as string[] });

  const fetchData = useCallback(async () => {
    try {
      const [usersRes, rolesRes] = await Promise.all([api.get('/api/users'), api.get('/api/roles')]);
      setUsers(usersRes.data.users);
      setRoles(rolesRes.data);
    } catch {}
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleOpen = (user?: User) => {
    if (user) {
      setEditing(user);
      setForm({ email: user.email, username: user.username, password: '', first_name: user.first_name || '', last_name: user.last_name || '', is_active: user.is_active, preferred_language: user.preferred_language, role_ids: user.roles.map(r => r.id) });
    } else {
      setEditing(null);
      setForm({ email: '', username: '', password: '', first_name: '', last_name: '', is_active: true, preferred_language: 'en', role_ids: [] });
    }
    setOpen(true);
  };

  const handleSave = async () => {
    try {
      const data: any = { ...form };
      if (!data.password) delete data.password;
      if (editing) {
        await api.put(`/api/users/${editing.id}`, data);
        enqueueSnackbar(t('users.updated'), { variant: 'success' });
      } else {
        await api.post('/api/users', data);
        enqueueSnackbar(t('users.created'), { variant: 'success' });
      }
      setOpen(false);
      fetchData();
    } catch (e: any) {
      enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' });
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(t('users.confirmDelete'))) return;
    try {
      await api.delete(`/api/users/${id}`);
      enqueueSnackbar(t('users.deleted'), { variant: 'success' });
      fetchData();
    } catch (e: any) {
      enqueueSnackbar(e.response?.data?.detail || t('common.error'), { variant: 'error' });
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight={600}>{t('users.title')}</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => handleOpen()}>
          {t('users.create')}
        </Button>
      </Box>
      <Card>
        <TableContainer>
          <Table aria-label={t('users.title')}>
            <TableHead>
              <TableRow>
                <TableCell>{t('users.username')}</TableCell>
                <TableCell>{t('users.email')}</TableCell>
                <TableCell>{t('users.firstName')}</TableCell>
                <TableCell>{t('users.lastName')}</TableCell>
                <TableCell>{t('users.roles')}</TableCell>
                <TableCell>{t('users.active')}</TableCell>
                <TableCell>{t('common.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>{user.username}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>{user.first_name}</TableCell>
                  <TableCell>{user.last_name}</TableCell>
                  <TableCell>{user.roles.map(r => <Chip key={r.id} label={r.name} size="small" sx={{ mr: 0.5 }} />)}</TableCell>
                  <TableCell><Chip label={user.is_active ? t('common.active') : t('common.inactive')} color={user.is_active ? 'success' : 'default'} size="small" /></TableCell>
                  <TableCell>
                    <IconButton size="small" onClick={() => handleOpen(user)} aria-label={t('common.edit')}><Edit /></IconButton>
                    <IconButton size="small" onClick={() => handleDelete(user.id)} color="error" aria-label={t('common.delete')}><Delete /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing ? t('users.edit') : t('users.create')}</DialogTitle>
        <DialogContent>
          <TextField fullWidth label={t('users.email')} value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} margin="normal" required type="email" />
          <TextField fullWidth label={t('users.username')} value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} margin="normal" required />
          <TextField fullWidth label={t('auth.password')} value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} margin="normal" type="password" required={!editing} helperText={editing ? 'Leave empty to keep current' : ''} />
          <TextField fullWidth label={t('users.firstName')} value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} margin="normal" />
          <TextField fullWidth label={t('users.lastName')} value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} margin="normal" />
          <FormControl fullWidth margin="normal">
            <InputLabel>{t('users.roles')}</InputLabel>
            <Select multiple value={form.role_ids} onChange={e => setForm({ ...form, role_ids: e.target.value as string[] })} input={<OutlinedInput label={t('users.roles')} />}>
              {roles.map(r => <MenuItem key={r.id} value={r.id}>{r.name}</MenuItem>)}
            </Select>
          </FormControl>
          <FormControl fullWidth margin="normal">
            <InputLabel>{t('users.language')}</InputLabel>
            <Select value={form.preferred_language} onChange={e => setForm({ ...form, preferred_language: e.target.value })} label={t('users.language')}>
              <MenuItem value="en">English</MenuItem>
              <MenuItem value="fr">Français</MenuItem>
              <MenuItem value="es">Español</MenuItem>
            </Select>
          </FormControl>
          <FormControlLabel control={<Switch checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />} label={t('users.active')} sx={{ mt: 1 }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={handleSave}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default UsersPage;
