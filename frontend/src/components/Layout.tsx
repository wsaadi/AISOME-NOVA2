import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Box, Drawer, AppBar, Toolbar, Typography, List, ListItemButton,
  ListItemIcon, ListItemText, IconButton, Divider, Avatar, Menu, MenuItem,
  useMediaQuery, useTheme, alpha, Tooltip,
} from '@mui/material';
import {
  Menu as MenuIcon, Dashboard, SmartToy, Assessment, SystemUpdate,
  Brightness4, Brightness7, ManageAccounts, Inventory, Logout,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { useThemeContext } from '../contexts/ThemeContext';

const DRAWER_WIDTH = 270;

const Layout: React.FC = () => {
  const { t } = useTranslation();
  const { user, logout, hasPermission } = useAuth();
  const { mode, toggleTheme } = useThemeContext();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const menuItems = [
    { path: '/dashboard', icon: <Dashboard />, label: t('nav.dashboard'), show: true },
    { divider: true, show: true },
    { path: '/catalog', icon: <SmartToy />, label: t('nav.catalog'), show: true },
    { path: '/catalog/manage', icon: <Inventory />, label: t('nav.catalogManagement'), show: hasPermission('catalog_management', 'read') },
    { divider: true, show: true },
    { path: '/consumption', icon: <Assessment />, label: t('nav.consumption'), show: hasPermission('consumption', 'read') },
    { divider: true, show: true },
    { path: '/settings', icon: <ManageAccounts />, label: t('nav.settings'), show: true },
    { path: '/system', icon: <SystemUpdate />, label: t('nav.system'), show: hasPermission('system', 'read') },
  ];

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ px: 2.5, py: 2.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Box sx={{
          width: 40, height: 40, borderRadius: '12px',
          background: 'linear-gradient(135deg, #818CF8 0%, #A78BFA 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 12px rgba(129,140,248,0.4)',
        }}>
          <SmartToy sx={{ color: '#fff', fontSize: 22 }} />
        </Box>
        <Box>
          <Typography variant="h6" noWrap sx={{ fontWeight: 800, color: '#fff', fontSize: '1.1rem', lineHeight: 1.2 }}>
            {t('app.name')}
          </Typography>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
            Admin Platform
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)', mx: 2 }} />

      <List sx={{ flex: 1, px: 1.5, py: 1 }} role="navigation" aria-label={t('nav.dashboard')}>
        {menuItems.filter((item) => item.show).map((item, index) =>
          'divider' in item ? (
            <Divider key={`div-${index}`} sx={{ my: 1, borderColor: 'rgba(255,255,255,0.06)' }} />
          ) : (
            <ListItemButton
              key={item.path}
              selected={location.pathname === item.path}
              onClick={() => { navigate(item.path!); if (isMobile) setMobileOpen(false); }}
              sx={{
                mb: 0.5,
                py: 1,
                px: 1.5,
                '& .MuiListItemIcon-root': {
                  color: location.pathname === item.path ? '#fff' : 'rgba(255,255,255,0.5)',
                  minWidth: 36,
                },
                '& .MuiListItemText-primary': {
                  color: location.pathname === item.path ? '#fff' : 'rgba(255,255,255,0.65)',
                  fontSize: '0.875rem',
                  fontWeight: location.pathname === item.path ? 600 : 400,
                },
                ...(location.pathname === item.path && {
                  background: 'rgba(255,255,255,0.12)',
                  backdropFilter: 'blur(10px)',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    left: 0, top: '50%', transform: 'translateY(-50%)',
                    width: 3, height: '60%',
                    borderRadius: '0 4px 4px 0',
                    background: 'linear-gradient(180deg, #818CF8, #A78BFA)',
                  },
                }),
              }}
              aria-current={location.pathname === item.path ? 'page' : undefined}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          )
        )}
      </List>

      <Box sx={{
        mx: 1.5, mb: 1.5, p: 1.5,
        borderRadius: '12px',
        background: 'rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'center', gap: 1.5,
      }}>
        <Avatar sx={{
          width: 36, height: 36,
          background: 'linear-gradient(135deg, #818CF8 0%, #A78BFA 100%)',
          fontSize: 14, fontWeight: 700,
        }}>
          {user?.username?.charAt(0).toUpperCase()}
        </Avatar>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="body2" sx={{ color: '#fff', fontWeight: 600, fontSize: '0.8rem' }} noWrap>
            {user?.first_name || user?.username}
          </Typography>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.7rem' }} noWrap>
            {user?.email}
          </Typography>
        </Box>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar
        position="fixed"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          ml: { md: `${DRAWER_WIDTH}px` },
          width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
          bgcolor: alpha(theme.palette.background.paper, 0.8),
          backdropFilter: 'blur(20px)',
          borderBottom: `1px solid ${theme.palette.divider}`,
        }}
        color="default"
        elevation={0}
      >
        <Toolbar>
          {isMobile && (
            <IconButton edge="start" onClick={() => setMobileOpen(!mobileOpen)} sx={{ mr: 2 }}
              aria-label="toggle navigation menu">
              <MenuIcon />
            </IconButton>
          )}
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="body1" fontWeight={600} color="text.primary">
              {menuItems.find(i => i.path === location.pathname)?.label || t('app.subtitle')}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t('app.subtitle')}
            </Typography>
          </Box>
          <Tooltip title={mode === 'dark' ? 'Light mode' : 'Dark mode'}>
            <IconButton
              onClick={toggleTheme}
              aria-label="toggle theme"
              sx={{
                bgcolor: alpha(theme.palette.primary.main, 0.08),
                mr: 1,
                '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.15) },
              }}
            >
              {mode === 'dark' ? <Brightness7 fontSize="small" /> : <Brightness4 fontSize="small" />}
            </IconButton>
          </Tooltip>
          <IconButton
            onClick={(e) => setAnchorEl(e.currentTarget)}
            aria-label="user menu"
            sx={{
              p: 0.5,
              border: `2px solid ${alpha(theme.palette.primary.main, 0.2)}`,
              '&:hover': { border: `2px solid ${alpha(theme.palette.primary.main, 0.4)}` },
            }}
          >
            <Avatar sx={{
              width: 32, height: 32,
              background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
              fontSize: 14, fontWeight: 700,
            }}>
              {user?.username?.charAt(0).toUpperCase()}
            </Avatar>
          </IconButton>
          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}
            PaperProps={{
              sx: { mt: 1, minWidth: 200, borderRadius: 2, border: `1px solid ${theme.palette.divider}` },
            }}
          >
            <Box sx={{ px: 2, py: 1.5 }}>
              <Typography variant="body2" fontWeight={600}>{user?.first_name || user?.username}</Typography>
              <Typography variant="caption" color="text.secondary">{user?.email}</Typography>
            </Box>
            <Divider />
            <MenuItem onClick={() => { setAnchorEl(null); navigate('/settings'); }} sx={{ py: 1.5 }}>
              <ListItemIcon><ManageAccounts fontSize="small" /></ListItemIcon>
              {t('nav.settings')}
            </MenuItem>
            <MenuItem onClick={logout} sx={{ py: 1.5, color: 'error.main' }}>
              <ListItemIcon><Logout fontSize="small" sx={{ color: 'error.main' }} /></ListItemIcon>
              {t('nav.logout')}
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {isMobile ? (
        <Drawer variant="temporary" open={mobileOpen} onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{ '& .MuiDrawer-paper': { width: DRAWER_WIDTH } }}>
          {drawer}
        </Drawer>
      ) : (
        <Drawer variant="permanent"
          sx={{ width: DRAWER_WIDTH, flexShrink: 0,
            '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' } }}>
          {drawer}
        </Drawer>
      )}

      <Box component="main" sx={{
        flexGrow: 1, p: { xs: 2, md: 3.5 }, mt: 8,
        width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
        maxWidth: '100%',
      }}>
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;
