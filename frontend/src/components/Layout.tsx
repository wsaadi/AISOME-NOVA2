import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Box, Drawer, AppBar, Toolbar, Typography, List, ListItemButton,
  ListItemIcon, ListItemText, IconButton, Divider, Avatar, Menu, MenuItem,
  useMediaQuery, useTheme,
} from '@mui/material';
import {
  Menu as MenuIcon, Dashboard, People, Security, Settings as SettingsIcon,
  SmartToy, Category, Assessment, MonetizationOn, Shield, SystemUpdate,
  Brightness4, Brightness7, ManageAccounts, Inventory,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { useThemeContext } from '../contexts/ThemeContext';

const DRAWER_WIDTH = 260;

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
    { path: '/users', icon: <People />, label: t('nav.users'), show: hasPermission('users', 'read') },
    { path: '/roles', icon: <Security />, label: t('nav.roles'), show: hasPermission('roles', 'read') },
    { path: '/llm-config', icon: <SettingsIcon />, label: t('nav.llmConfig'), show: hasPermission('llm_config', 'read') },
    { divider: true, show: true },
    { path: '/consumption', icon: <Assessment />, label: t('nav.consumption'), show: hasPermission('consumption', 'read') },
    { path: '/quotas', icon: <MonetizationOn />, label: t('nav.quotas'), show: hasPermission('quotas', 'read') },
    { path: '/costs', icon: <MonetizationOn />, label: t('nav.costs'), show: hasPermission('costs', 'read') },
    { divider: true, show: true },
    { path: '/moderation', icon: <Shield />, label: t('nav.moderation'), show: hasPermission('moderation', 'read') },
    { path: '/catalog', icon: <SmartToy />, label: t('nav.catalog'), show: true },
    { path: '/catalog/manage', icon: <Inventory />, label: t('nav.catalogManagement'), show: hasPermission('catalog_management', 'read') },
    { divider: true, show: true },
    { path: '/settings', icon: <ManageAccounts />, label: t('nav.settings'), show: true },
    { path: '/system', icon: <SystemUpdate />, label: t('nav.system'), show: hasPermission('system', 'read') },
  ];

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Toolbar sx={{ px: 2 }}>
        <SmartToy sx={{ mr: 1, color: 'primary.main' }} />
        <Typography variant="h6" noWrap fontWeight={700} color="primary">
          {t('app.name')}
        </Typography>
      </Toolbar>
      <Divider />
      <List sx={{ flex: 1, px: 1 }} role="navigation" aria-label={t('nav.dashboard')}>
        {menuItems.filter((item) => item.show).map((item, index) =>
          'divider' in item ? (
            <Divider key={`div-${index}`} sx={{ my: 1 }} />
          ) : (
            <ListItemButton
              key={item.path}
              selected={location.pathname === item.path}
              onClick={() => { navigate(item.path!); if (isMobile) setMobileOpen(false); }}
              sx={{ borderRadius: 1, mb: 0.5 }}
              aria-current={location.pathname === item.path ? 'page' : undefined}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          )
        )}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1, boxShadow: 1 }}
        color="default" enableColorOnDark>
        <Toolbar>
          {isMobile && (
            <IconButton edge="start" onClick={() => setMobileOpen(!mobileOpen)} sx={{ mr: 2 }}
              aria-label="toggle navigation menu">
              <MenuIcon />
            </IconButton>
          )}
          <Typography variant="h6" noWrap sx={{ flexGrow: 1 }}>
            {t('app.subtitle')}
          </Typography>
          <IconButton onClick={toggleTheme} aria-label="toggle theme">
            {mode === 'dark' ? <Brightness7 /> : <Brightness4 />}
          </IconButton>
          <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} aria-label="user menu">
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: 14 }}>
              {user?.username?.charAt(0).toUpperCase()}
            </Avatar>
          </IconButton>
          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
            <MenuItem disabled>
              <Typography variant="body2">{user?.email}</Typography>
            </MenuItem>
            <Divider />
            <MenuItem onClick={() => { setAnchorEl(null); navigate('/settings'); }}>
              {t('nav.settings')}
            </MenuItem>
            <MenuItem onClick={logout}>{t('nav.logout')}</MenuItem>
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
      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8, width: { md: `calc(100% - ${DRAWER_WIDTH}px)` } }}>
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;
