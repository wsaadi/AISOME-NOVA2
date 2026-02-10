import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Box, Grid, Card, CardContent, Typography, Skeleton, alpha, useTheme } from '@mui/material';
import { People, SmartToy, Assessment, Shield } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

const GRADIENTS = [
  'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)',
  'linear-gradient(135deg, #7C3AED 0%, #EC4899 100%)',
  'linear-gradient(135deg, #059669 0%, #10B981 100%)',
  'linear-gradient(135deg, #F59E0B 0%, #EF4444 100%)',
];

const StatCard: React.FC<{ title: string; value: string | number; icon: React.ReactNode; gradient: string }> = ({ title, value, icon, gradient }) => {
  const theme = useTheme();
  return (
    <Card sx={{
      position: 'relative',
      overflow: 'hidden',
      '&:hover': { transform: 'translateY(-2px)' },
      transition: 'all 0.2s ease',
    }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="body2" color="text.secondary" fontWeight={500} sx={{ mb: 0.5 }}>
              {title}
            </Typography>
            <Typography variant="h3" fontWeight={700} sx={{ letterSpacing: '-0.02em' }}>
              {value}
            </Typography>
          </Box>
          <Box sx={{
            p: 1.5, borderRadius: '14px',
            background: gradient,
            color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: `0 4px 14px ${alpha(theme.palette.primary.main, 0.25)}`,
          }}>
            {icon}
          </Box>
        </Box>
        <Box sx={{
          position: 'absolute',
          bottom: 0, right: 0,
          width: 120, height: 120,
          borderRadius: '50%',
          background: gradient,
          opacity: 0.04,
          transform: 'translate(30%, 30%)',
        }} />
      </CardContent>
    </Card>
  );
};

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const theme = useTheme();
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
      <Box sx={{
        mb: 4, p: 4, borderRadius: 4,
        background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.08)} 0%, ${alpha(theme.palette.secondary.main, 0.08)} 100%)`,
        border: `1px solid ${alpha(theme.palette.primary.main, 0.12)}`,
      }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          {t('auth.welcome')}, {user?.first_name || user?.username}
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {t('app.subtitle')}
        </Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          {stats ? (
            <StatCard title={t('nav.users')} value={stats.users} icon={<People />} gradient={GRADIENTS[0]} />
          ) : (
            <Skeleton variant="rounded" height={130} sx={{ borderRadius: 4 }} />
          )}
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          {stats ? (
            <StatCard title={t('nav.catalog')} value={stats.agents} icon={<SmartToy />} gradient={GRADIENTS[1]} />
          ) : (
            <Skeleton variant="rounded" height={130} sx={{ borderRadius: 4 }} />
          )}
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard title={t('nav.consumption')} value="-" icon={<Assessment />} gradient={GRADIENTS[2]} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard title={t('nav.moderation')} value={t('common.active')} icon={<Shield />} gradient={GRADIENTS[3]} />
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;
