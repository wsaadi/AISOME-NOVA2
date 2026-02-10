import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Card, CardContent, Button, Alert, CircularProgress,
  List, ListItem, ListItemText, Chip, alpha, useTheme, Avatar,
} from '@mui/material';
import { SystemUpdate, CheckCircle, NewReleases, Info } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

const SystemPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const [version, setVersion] = useState('');
  const [updateInfo, setUpdateInfo] = useState<any>(null);
  const [checking, setChecking] = useState(false);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    api.get('/api/system/version').then(res => setVersion(res.data.version)).catch(() => {});
  }, []);

  const checkUpdates = async () => {
    setChecking(true);
    try {
      const res = await api.get('/api/system/check-update');
      setUpdateInfo(res.data);
    } catch { enqueueSnackbar(t('common.error'), { variant: 'error' }); }
    setChecking(false);
  };

  const applyUpdate = async () => {
    setUpdating(true);
    try {
      const res = await api.post('/api/system/update');
      if (res.data.success) {
        enqueueSnackbar(t('common.success'), { variant: 'success' });
      } else {
        enqueueSnackbar(res.data.error || t('common.error'), { variant: 'error' });
      }
    } catch { enqueueSnackbar(t('common.error'), { variant: 'error' }); }
    setUpdating(false);
  };

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} gutterBottom>{t('system.title')}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>{t('app.subtitle')}</Typography>

      <Card sx={{ mb: 3, overflow: 'hidden' }}>
        <Box sx={{ height: 4, background: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)' }} />
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
            <Avatar variant="rounded" sx={{
              width: 52, height: 52,
              background: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)',
              borderRadius: '14px',
            }}>
              <SystemUpdate sx={{ fontSize: 28 }} />
            </Avatar>
            <Box>
              <Typography variant="h6" fontWeight={600}>{t('system.currentVersion')}</Typography>
              <Chip label={`v${version}`} color="primary" sx={{ mt: 0.5, fontWeight: 600 }} />
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <Button variant="outlined" onClick={checkUpdates} disabled={checking} sx={{ borderRadius: 2 }}>
              {checking ? <CircularProgress size={20} sx={{ mr: 1 }} /> : null}
              {t('system.checkUpdate')}
            </Button>
            {updateInfo && updateInfo.updates_available && (
              <Button variant="contained" color="warning" onClick={applyUpdate} disabled={updating} sx={{ borderRadius: 2 }}>
                {updating ? <CircularProgress size={20} sx={{ mr: 1 }} /> : null}
                {t('system.applyUpdate')}
              </Button>
            )}
          </Box>
        </CardContent>
      </Card>

      {updateInfo && (
        <Card>
          <CardContent sx={{ p: 3 }}>
            {updateInfo.updates_available ? (
              <>
                <Alert severity="info" icon={<NewReleases />} sx={{ mb: 2, borderRadius: 2 }}>
                  {t('system.updateAvailable')} - {updateInfo.pending_commits} {t('system.pendingCommits')}
                </Alert>
                <List dense>
                  {updateInfo.commit_messages?.map((msg: string, i: number) => (
                    <ListItem key={i} sx={{
                      borderRadius: 2, mb: 0.5,
                      bgcolor: alpha(theme.palette.info.main, 0.04),
                    }}>
                      <ListItemText primary={msg} />
                    </ListItem>
                  ))}
                </List>
              </>
            ) : (
              <Alert severity="success" icon={<CheckCircle />} sx={{ borderRadius: 2 }}>
                {t('system.upToDate')}
              </Alert>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default SystemPage;
