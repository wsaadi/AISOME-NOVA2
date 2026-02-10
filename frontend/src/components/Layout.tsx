import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Box, Drawer, AppBar, Toolbar, Typography, List, ListItemButton,
  ListItemIcon, ListItemText, IconButton, Divider, Avatar, Menu, MenuItem,
  useMediaQuery, useTheme, alpha, Tooltip, TextField,
} from '@mui/material';
import {
  Menu as MenuIcon, Dashboard, SmartToy, Assessment, SystemUpdate,
  Brightness4, Brightness7, ManageAccounts, Inventory, Logout,
  ChevronLeft, ChevronRight, Edit as EditIcon, Check, Close,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { useThemeContext } from '../contexts/ThemeContext';
import api from '../services/api';

const DRAWER_WIDTH = 270;
const DRAWER_COLLAPSED_WIDTH = 72;

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
  const [collapsed, setCollapsed] = useState(false);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [platformName, setPlatformName] = useState('');
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState('');
  const nameInputRef = useRef<HTMLInputElement>(null);

  const currentWidth = collapsed && !isMobile ? DRAWER_COLLAPSED_WIDTH : DRAWER_WIDTH;

  const fetchLogo = useCallback(async () => {
    try {
      const res = await api.get('/api/system/logo', { responseType: 'blob' });
      if (res.data.size > 0) {
        setLogoUrl(URL.createObjectURL(res.data));
      }
    } catch {
      setLogoUrl(null);
    }
  }, []);

  useEffect(() => {
    fetchLogo();
    const saved = localStorage.getItem('platform_name');
    if (saved) setPlatformName(saved);
  }, [fetchLogo]);

  const handleStartEditName = () => {
    setNameInput(platformName || t('app.name'));
    setEditingName(true);
    setTimeout(() => nameInputRef.current?.focus(), 50);
  };

  const handleSaveName = () => {
    const trimmed = nameInput.trim();
    if (trimmed) {
      setPlatformName(trimmed);
      localStorage.setItem('platform_name', trimmed);
    }
    setEditingName(false);
  };

  const handleCancelEditName = () => {
    setEditingName(false);
  };

  const displayName = platformName || t('app.name');

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

  const isCollapsed = collapsed && !isMobile;

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{
        px: isCollapsed ? 1 : 2.5, py: 2.5,
        display: 'flex', alignItems: 'center', gap: 1.5,
        justifyContent: isCollapsed ? 'center' : 'flex-start',
        minHeight: 72,
      }}>
        {logoUrl ? (
          <Box
            component="img"
            src={logoUrl}
            alt="Logo"
            sx={{
              width: 40, height: 40, borderRadius: '12px',
              objectFit: 'cover',
              boxShadow: '0 4px 12px rgba(129,140,248,0.4)',
              flexShrink: 0,
            }}
          />
        ) : (
          <Box sx={{
            width: 40, height: 40, borderRadius: '12px',
            background: 'linear-gradient(135deg, #818CF8 0%, #A78BFA 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(129,140,248,0.4)',
            flexShrink: 0,
          }}>
            <SmartToy sx={{ color: '#fff', fontSize: 22 }} />
          </Box>
        )}
        {!isCollapsed && (
          <Box sx={{ flex: 1, minWidth: 0 }}>
            {editingName ? (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <TextField
                  inputRef={nameInputRef}
                  value={nameInput}
                  onChange={e => setNameInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleSaveName(); if (e.key === 'Escape') handleCancelEditName(); }}
                  variant="standard"
                  size="small"
                  sx={{
                    flex: 1,
                    '& .MuiInput-root': { color: '#fff', fontSize: '1rem', fontWeight: 800 },
                    '& .MuiInput-underline:before': { borderBottomColor: 'rgba(255,255,255,0.3)' },
                    '& .MuiInput-underline:hover:before': { borderBottomColor: 'rgba(255,255,255,0.5)' },
                    '& .MuiInput-underline:after': { borderBottomColor: '#818CF8' },
                  }}
                />
                <IconButton size="small" onClick={handleSaveName} sx={{ color: '#10B981', p: 0.25 }}>
                  <Check sx={{ fontSize: 16 }} />
                </IconButton>
                <IconButton size="small" onClick={handleCancelEditName} sx={{ color: 'rgba(255,255,255,0.5)', p: 0.25 }}>
                  <Close sx={{ fontSize: 16 }} />
                </IconButton>
              </Box>
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Typography variant="h6" noWrap sx={{ fontWeight: 800, color: '#fff', fontSize: '1.1rem', lineHeight: 1.2 }}>
                  {displayName}
                </Typography>
                <IconButton size="small" onClick={handleStartEditName} sx={{ color: 'rgba(255,255,255,0.35)', p: 0.25, '&:hover': { color: 'rgba(255,255,255,0.7)' } }}>
                  <EditIcon sx={{ fontSize: 14 }} />
                </IconButton>
              </Box>
            )}
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
              Admin Platform
            </Typography>
          </Box>
        )}
      </Box>

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)', mx: isCollapsed ? 1 : 2 }} />

      <List sx={{ flex: 1, px: isCollapsed ? 0.75 : 1.5, py: 1 }} role="navigation" aria-label={t('nav.dashboard')}>
        {menuItems.filter((item) => item.show).map((item, index) =>
          'divider' in item ? (
            <Divider key={`div-${index}`} sx={{ my: 1, borderColor: 'rgba(255,255,255,0.06)' }} />
          ) : isCollapsed ? (
            <Tooltip key={item.path} title={item.label} placement="right" arrow>
              <ListItemButton
                selected={location.pathname === item.path}
                onClick={() => { navigate(item.path!); if (isMobile) setMobileOpen(false); }}
                sx={{
                  mb: 0.5,
                  py: 1,
                  px: 1.5,
                  justifyContent: 'center',
                  '& .MuiListItemIcon-root': {
                    color: location.pathname === item.path ? '#fff' : 'rgba(255,255,255,0.5)',
                    minWidth: 'auto',
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
              </ListItemButton>
            </Tooltip>
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

      {/* Collapse toggle button */}
      {!isMobile && (
        <Box sx={{ px: isCollapsed ? 0.75 : 1.5, mb: 0.5 }}>
          <Tooltip title={collapsed ? t('common.expand') || 'Expand' : t('common.collapse') || 'Collapse'} placement="right">
            <ListItemButton
              onClick={() => setCollapsed(!collapsed)}
              sx={{
                py: 1,
                px: 1.5,
                justifyContent: isCollapsed ? 'center' : 'flex-start',
                borderRadius: '8px',
                '& .MuiListItemIcon-root': {
                  color: 'rgba(255,255,255,0.5)',
                  minWidth: isCollapsed ? 'auto' : 36,
                },
                '& .MuiListItemText-primary': {
                  color: 'rgba(255,255,255,0.5)',
                  fontSize: '0.8rem',
                },
                '&:hover': {
                  background: 'rgba(255,255,255,0.06)',
                },
              }}
            >
              <ListItemIcon>
                {collapsed ? <ChevronRight /> : <ChevronLeft />}
              </ListItemIcon>
              {!isCollapsed && <ListItemText primary={t('common.collapse') || 'Collapse'} />}
            </ListItemButton>
          </Tooltip>
        </Box>
      )}

      {/* User info */}
      <Box sx={{
        mx: isCollapsed ? 0.75 : 1.5, mb: 1.5, p: isCollapsed ? 1 : 1.5,
        borderRadius: '12px',
        background: 'rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'center', gap: 1.5,
        justifyContent: isCollapsed ? 'center' : 'flex-start',
      }}>
        <Avatar sx={{
          width: 36, height: 36,
          background: 'linear-gradient(135deg, #818CF8 0%, #A78BFA 100%)',
          fontSize: 14, fontWeight: 700,
          flexShrink: 0,
        }}>
          {user?.username?.charAt(0).toUpperCase()}
        </Avatar>
        {!isCollapsed && (
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="body2" sx={{ color: '#fff', fontWeight: 600, fontSize: '0.8rem' }} noWrap>
              {user?.first_name || user?.username}
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.7rem' }} noWrap>
              {user?.email}
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar
        position="fixed"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          ml: { md: `${currentWidth}px` },
          width: { md: `calc(100% - ${currentWidth}px)` },
          bgcolor: alpha(theme.palette.background.paper, 0.8),
          backdropFilter: 'blur(20px)',
          borderBottom: `1px solid ${theme.palette.divider}`,
          transition: 'width 0.2s ease, margin-left 0.2s ease',
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
          sx={{
            width: currentWidth, flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: currentWidth, boxSizing: 'border-box',
              transition: 'width 0.2s ease',
              overflowX: 'hidden',
            },
          }}>
          {drawer}
        </Drawer>
      )}

      <Box component="main" sx={{
        flexGrow: 1, p: { xs: 2, md: 3.5 }, mt: 8,
        width: { md: `calc(100% - ${currentWidth}px)` },
        maxWidth: '100%',
        transition: 'width 0.2s ease',
      }}>
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;
