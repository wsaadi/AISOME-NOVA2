import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Box, Grid, Card, CardContent, Typography, Skeleton } from '@mui/material';
import { People, SmartToy, Assessment, Shield } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

const StatCard: React.FC<{ title: string; value: string | number; icon: React.ReactNode; color: string }> = ({ title, value, icon, color }) => (
  <Card>
    <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: `${color}15`, color }}>
        {icon}
      </Box>
      <Box>
        <Typography variant="body2" color="text.secondary">{title}</Typography>
        <Typography variant="h5" fontWeight={600}>{value}</Typography>
      </Box>
    </CardContent>
  </Card>
);

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [usersRes, agentsRes] = await Promise.allSettled([
          api.get('/api/users?limit=1'),
          api.get('/api/agents'),
        ]);
        setStats({
          users: usersRes.status === 'fulfilled' ? usersRes.value.data.total : '-',
          agents: agentsRes.status === 'fulfilled' ? agentsRes.value.data.length : '-',
        });
      } catch {
        setStats({ users: '-', agents: '-' });
      }
    };
    fetchStats();
  }, []);

  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={600}>
        {t('auth.welcome')}, {user?.first_name || user?.username}
      </Typography>
      <Grid container spacing={3} sx={{ mt: 1 }}>
        <Grid item xs={12} sm={6} md={3}>
          {stats ? (
            <StatCard title={t('nav.users')} value={stats.users} icon={<People />} color="#1976d2" />
          ) : (
            <Skeleton variant="rounded" height={100} />
          )}
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          {stats ? (
            <StatCard title={t('nav.catalog')} value={stats.agents} icon={<SmartToy />} color="#9c27b0" />
          ) : (
            <Skeleton variant="rounded" height={100} />
          )}
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard title={t('nav.consumption')} value="-" icon={<Assessment />} color="#2e7d32" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard title={t('nav.moderation')} value={t('common.active')} icon={<Shield />} color="#ed6c02" />
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;
