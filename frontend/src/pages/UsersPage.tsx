import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Switch, FormControlLabel, IconButton, Chip, Card, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow, Select,
  MenuItem, FormControl, InputLabel, OutlinedInput, Avatar, alpha, useTheme,
  InputAdornment, Tooltip,
} from '@mui/material';
import { Add, Edit, Delete, Search, PersonAdd } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

interface User {
  id: string; email: string; username: string; first_name: string | null;
  last_name: string | null; is_active: boolean; roles: { id: string; name: string }[];
  preferred_language: string;
}
interface Role { id: string; name: string; }

const USER_COLORS = [
  'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)',
  'linear-gradient(135deg, #059669 0%, #10B981 100%)',
  'linear-gradient(135deg, #D97706 0%, #F59E0B 100%)',
  'linear-gradient(135deg, #DC2626 0%, #EF4444 100%)',
  'linear-gradient(135deg, #7C3AED 0%, #EC4899 100%)',
  'linear-gradient(135deg, #2563EB 0%, #3B82F6 100%)',
];

const UsersPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [search, setSearch] = useState('');
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

  const filteredUsers = users.filter(u =>
    u.username.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase()) ||
    u.first_name?.toLowerCase().includes(search.toLowerCase()) ||
    u.last_name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>{t('users.title')}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {users.length} {t('users.title').toLowerCase()}
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<PersonAdd />} onClick={() => handleOpen()} sx={{ px: 3 }}>
          {t('users.create')}
        </Button>
      </Box>

      <TextField
        placeholder={`${t('common.search')}...`}
        value={search}
        onChange={e => setSearch(e.target.value)}
        InputProps={{
          startAdornment: <InputAdornment position="start"><Search color="action" /></InputAdornment>,
        }}
        size="small"
        sx={{ mb: 3, minWidth: 300, '& .MuiOutlinedInput-root': { bgcolor: 'background.paper' } }}
      />

      <Card>
        <TableContainer>
          <Table aria-label={t('users.title')}>
            <TableHead>
              <TableRow>
                <TableCell>{t('users.username')}</TableCell>
                <TableCell>{t('users.email')}</TableCell>
                <TableCell>{t('users.roles')}</TableCell>
                <TableCell>{t('users.active')}</TableCell>
                <TableCell align="right">{t('common.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredUsers.map((user, index) => (
                <TableRow key={user.id} hover>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Avatar sx={{
                        width: 38, height: 38,
                        background: USER_COLORS[index % USER_COLORS.length],
                        fontSize: 14, fontWeight: 700,
                      }}>
                        {user.username.charAt(0).toUpperCase()}
                      </Avatar>
                      <Box>
                        <Typography variant="body2" fontWeight={600}>
                          {user.first_name && user.last_name
                            ? `${user.first_name} ${user.last_name}`
                            : user.username}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          @{user.username}
                        </Typography>
                      </Box>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">{user.email}</Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {user.roles.map(r => (
                        <Chip key={r.id} label={r.name} size="small" color="primary" />
                      ))}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={user.is_active ? t('common.active') : t('common.inactive')}
                      color={user.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title={t('common.edit')}>
                      <IconButton size="small" onClick={() => handleOpen(user)} sx={{
                        bgcolor: alpha(theme.palette.primary.main, 0.08),
                        mr: 0.5,
                        '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.15) },
                      }}>
                        <Edit fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title={t('common.delete')}>
                      <IconButton size="small" onClick={() => handleDelete(user.id)} sx={{
                        bgcolor: alpha(theme.palette.error.main, 0.08),
                        '&:hover': { bgcolor: alpha(theme.palette.error.main, 0.15) },
                        color: 'error.main',
                      }}>
                        <Delete fontSize="small" />
                      </IconButton>
                    </Tooltip>
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
          <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
            <TextField fullWidth label={t('users.firstName')} value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} />
            <TextField fullWidth label={t('users.lastName')} value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} />
          </Box>
          <TextField fullWidth label={t('users.email')} value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} margin="normal" required type="email" />
          <TextField fullWidth label={t('users.username')} value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} margin="normal" required />
          <TextField fullWidth label={t('auth.password')} value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} margin="normal" type="password" required={!editing} helperText={editing ? 'Leave empty to keep current' : ''} />
          <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel>{t('users.roles')}</InputLabel>
              <Select multiple value={form.role_ids} onChange={e => setForm({ ...form, role_ids: e.target.value as string[] })} input={<OutlinedInput label={t('users.roles')} />}>
                {roles.map(r => <MenuItem key={r.id} value={r.id}>{r.name}</MenuItem>)}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>{t('users.language')}</InputLabel>
              <Select value={form.preferred_language} onChange={e => setForm({ ...form, preferred_language: e.target.value })} label={t('users.language')}>
                <MenuItem value="en">English</MenuItem>
                <MenuItem value="fr">Fran\u00e7ais</MenuItem>
                <MenuItem value="es">Espa\u00f1ol</MenuItem>
              </Select>
            </FormControl>
          </Box>
          <FormControlLabel control={<Switch checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />} label={t('users.active')} sx={{ mt: 2 }} />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={handleSave}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default UsersPage;
