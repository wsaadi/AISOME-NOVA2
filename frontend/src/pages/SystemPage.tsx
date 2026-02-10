import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Card, CardContent, Button, Alert, CircularProgress,
  List, ListItem, ListItemText, Chip,
} from '@mui/material';
import { SystemUpdate, CheckCircle, NewReleases } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

const SystemPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
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
      <Typography variant="h4" fontWeight={600} gutterBottom>{t('system.title')}</Typography>
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <SystemUpdate color="primary" sx={{ fontSize: 40 }} />
            <Box>
              <Typography variant="h6">{t('system.currentVersion')}</Typography>
              <Chip label={`v${version}`} color="primary" />
            </Box>
          </Box>
          <Button variant="outlined" onClick={checkUpdates} disabled={checking} sx={{ mr: 2 }}>
            {checking ? <CircularProgress size={20} sx={{ mr: 1 }} /> : null}
            {t('system.checkUpdate')}
          </Button>
          {updateInfo && updateInfo.updates_available && (
            <Button variant="contained" color="warning" onClick={applyUpdate} disabled={updating}>
              {updating ? <CircularProgress size={20} sx={{ mr: 1 }} /> : null}
              {t('system.applyUpdate')}
            </Button>
          )}
        </CardContent>
      </Card>
      {updateInfo && (
        <Card>
          <CardContent>
            {updateInfo.updates_available ? (
              <>
                <Alert severity="info" icon={<NewReleases />} sx={{ mb: 2 }}>
                  {t('system.updateAvailable')} - {updateInfo.pending_commits} {t('system.pendingCommits')}
                </Alert>
                <List dense>
                  {updateInfo.commit_messages?.map((msg: string, i: number) => (
                    <ListItem key={i}><ListItemText primary={msg} /></ListItem>
                  ))}
                </List>
              </>
            ) : (
              <Alert severity="success" icon={<CheckCircle />}>{t('system.upToDate')}</Alert>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default SystemPage;
