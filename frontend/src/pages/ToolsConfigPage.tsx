import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, Card, CardContent, Grid, Chip, Switch, FormControlLabel,
  Avatar, alpha, useTheme, Tabs, Tab, Accordion, AccordionSummary,
  AccordionDetails, List, ListItem, ListItemText, Alert, TextField,
  InputAdornment, Tooltip, IconButton,
} from '@mui/material';
import {
  Build, Extension, ExpandMore, Search, Category, CheckCircle,
  Info, Storage, Code, Refresh,
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import api from '../services/api';

interface ToolParam {
  name: string;
  type: string;
  required?: boolean;
  description?: string;
  default?: any;
}

interface ToolExample {
  description: string;
  input: Record<string, any>;
  output: Record<string, any>;
}

interface ToolInfo {
  slug: string;
  name: string;
  description: string;
  version: string;
  category: string;
  execution_mode: string;
  timeout_seconds: number;
  input_schema: ToolParam[];
  output_schema: ToolParam[];
  examples: ToolExample[];
  tags?: string[];
}

interface ConnectorAction {
  name: string;
  description: string;
  input_schema: ToolParam[];
  output_schema: ToolParam[];
}

interface ConnectorInfo {
  slug: string;
  name: string;
  description: string;
  version: string;
  category: string;
  auth_type: string;
  config_schema: ToolParam[];
  actions: ConnectorAction[];
  is_connected?: boolean;
  is_configured?: boolean;
  tags?: string[];
}

type EnabledConfig = Record<string, boolean>;

const STORAGE_KEY = 'platform_tools_config';

function loadConfig(): EnabledConfig {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch { return {}; }
}

function saveConfig(config: EnabledConfig) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

const CATEGORY_COLORS: Record<string, string> = {
  data: 'linear-gradient(135deg, #059669 0%, #10B981 100%)',
  text: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)',
  ai: 'linear-gradient(135deg, #7C3AED 0%, #EC4899 100%)',
  file: 'linear-gradient(135deg, #D97706 0%, #F59E0B 100%)',
  media: 'linear-gradient(135deg, #DC2626 0%, #EF4444 100%)',
  general: 'linear-gradient(135deg, #2563EB 0%, #3B82F6 100%)',
  saas: 'linear-gradient(135deg, #0891B2 0%, #06B6D4 100%)',
  messaging: 'linear-gradient(135deg, #059669 0%, #10B981 100%)',
  storage: 'linear-gradient(135deg, #D97706 0%, #F59E0B 100%)',
  database: 'linear-gradient(135deg, #DC2626 0%, #EF4444 100%)',
};

function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || 'linear-gradient(135deg, #6B7280 0%, #9CA3AF 100%)';
}

/* ── Tool Card ── */
const ToolCard: React.FC<{
  tool: ToolInfo;
  enabled: boolean;
  onToggle: (slug: string, enabled: boolean) => void;
}> = ({ tool, enabled, onToggle }) => {
  const { t } = useTranslation();
  const theme = useTheme();

  return (
    <Card sx={{
      overflow: 'hidden',
      opacity: enabled ? 1 : 0.7,
      transition: 'all 0.2s ease',
      '&:hover': { transform: 'translateY(-2px)', opacity: 1 },
    }}>
      <Box sx={{ height: 4, background: getCategoryColor(tool.category) }} />
      <CardContent sx={{ pt: 2.5 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Avatar variant="rounded" sx={{
              width: 44, height: 44,
              background: getCategoryColor(tool.category),
              borderRadius: '12px',
            }}>
              <Build />
            </Avatar>
            <Box>
              <Typography variant="subtitle1" fontWeight={700}>{tool.name}</Typography>
              <Typography variant="caption" color="text.secondary" fontFamily="monospace">{tool.slug}</Typography>
            </Box>
          </Box>
          <Switch
            checked={enabled}
            onChange={e => onToggle(tool.slug, e.target.checked)}
            color="primary"
          />
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, minHeight: 40 }}>
          {tool.description}
        </Typography>

        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 1.5 }}>
          <Chip label={tool.category} size="small" sx={{
            background: alpha(theme.palette.primary.main, 0.1),
            color: theme.palette.primary.main,
            fontWeight: 600,
            fontSize: '0.7rem',
          }} />
          <Chip label={`v${tool.version}`} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
          <Chip
            label={tool.execution_mode}
            size="small"
            color={tool.execution_mode === 'sync' ? 'success' : 'info'}
            sx={{ fontSize: '0.7rem' }}
          />
          <Chip label={`${tool.timeout_seconds}s`} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
        </Box>

        <Accordion sx={{ mt: 1, '&:before': { display: 'none' }, boxShadow: 'none', bgcolor: 'transparent' }}>
          <AccordionSummary expandIcon={<ExpandMore />} sx={{ px: 0, minHeight: 32, '& .MuiAccordionSummary-content': { my: 0.5 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Code fontSize="small" />
              <Typography variant="body2" fontWeight={500}>{t('tools.schema')}</Typography>
              <Chip label={`${tool.input_schema.length} in / ${tool.output_schema.length} out`} size="small" sx={{ height: 20, fontSize: '0.65rem' }} />
            </Box>
          </AccordionSummary>
          <AccordionDetails sx={{ px: 0 }}>
            {tool.input_schema.length > 0 && (
              <>
                <Typography variant="caption" fontWeight={600} color="text.secondary">{t('tools.inputParams')}</Typography>
                <List dense disablePadding>
                  {tool.input_schema.map(p => (
                    <ListItem key={p.name} sx={{ px: 1, py: 0.25, borderRadius: 1, bgcolor: alpha(theme.palette.primary.main, 0.04), mb: 0.25 }}>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Typography variant="caption" fontWeight={600} fontFamily="monospace">{p.name}</Typography>
                            <Chip label={p.type} size="small" sx={{ height: 16, fontSize: '0.6rem' }} />
                            {p.required && <Chip label="required" size="small" color="error" sx={{ height: 16, fontSize: '0.6rem' }} />}
                          </Box>
                        }
                        secondary={p.description}
                        secondaryTypographyProps={{ variant: 'caption' }}
                      />
                    </ListItem>
                  ))}
                </List>
              </>
            )}
            {tool.output_schema.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="caption" fontWeight={600} color="text.secondary">{t('tools.outputParams')}</Typography>
                <List dense disablePadding>
                  {tool.output_schema.map(p => (
                    <ListItem key={p.name} sx={{ px: 1, py: 0.25, borderRadius: 1, bgcolor: alpha(theme.palette.success.main, 0.04), mb: 0.25 }}>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Typography variant="caption" fontWeight={600} fontFamily="monospace">{p.name}</Typography>
                            <Chip label={p.type} size="small" sx={{ height: 16, fontSize: '0.6rem' }} />
                          </Box>
                        }
                        secondary={p.description}
                        secondaryTypographyProps={{ variant: 'caption' }}
                      />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
            {tool.examples && tool.examples.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="caption" fontWeight={600} color="text.secondary">{t('tools.examples')}</Typography>
                {tool.examples.map((ex, i) => (
                  <Box key={i} sx={{ mt: 0.5, p: 1, borderRadius: 1, bgcolor: alpha(theme.palette.info.main, 0.04) }}>
                    <Typography variant="caption" fontWeight={600}>{ex.description}</Typography>
                    <Typography variant="caption" component="pre" sx={{ fontFamily: 'monospace', fontSize: '0.65rem', whiteSpace: 'pre-wrap', mt: 0.25 }}>
                      {JSON.stringify(ex.input, null, 2)}
                    </Typography>
                  </Box>
                ))}
              </Box>
            )}
          </AccordionDetails>
        </Accordion>
      </CardContent>
    </Card>
  );
};

/* ── Connector Card ── */
const ConnectorCard: React.FC<{
  connector: ConnectorInfo;
  enabled: boolean;
  onToggle: (slug: string, enabled: boolean) => void;
}> = ({ connector, enabled, onToggle }) => {
  const { t } = useTranslation();
  const theme = useTheme();

  return (
    <Card sx={{
      overflow: 'hidden',
      opacity: enabled ? 1 : 0.7,
      transition: 'all 0.2s ease',
      '&:hover': { transform: 'translateY(-2px)', opacity: 1 },
    }}>
      <Box sx={{ height: 4, background: getCategoryColor(connector.category) }} />
      <CardContent sx={{ pt: 2.5 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Avatar variant="rounded" sx={{
              width: 44, height: 44,
              background: getCategoryColor(connector.category),
              borderRadius: '12px',
            }}>
              <Extension />
            </Avatar>
            <Box>
              <Typography variant="subtitle1" fontWeight={700}>{connector.name}</Typography>
              <Typography variant="caption" color="text.secondary" fontFamily="monospace">{connector.slug}</Typography>
            </Box>
          </Box>
          <Switch
            checked={enabled}
            onChange={e => onToggle(connector.slug, e.target.checked)}
            color="primary"
          />
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, minHeight: 40 }}>
          {connector.description}
        </Typography>

        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 1.5 }}>
          <Chip label={connector.category} size="small" sx={{
            background: alpha(theme.palette.primary.main, 0.1),
            color: theme.palette.primary.main,
            fontWeight: 600,
            fontSize: '0.7rem',
          }} />
          <Chip label={`v${connector.version}`} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
          <Chip
            icon={<Storage sx={{ fontSize: '0.8rem !important' }} />}
            label={connector.auth_type}
            size="small"
            variant="outlined"
            sx={{ fontSize: '0.7rem' }}
          />
          {connector.is_connected && (
            <Chip icon={<CheckCircle />} label={t('tools.connected')} size="small" color="success" sx={{ fontSize: '0.7rem' }} />
          )}
          {connector.is_configured && !connector.is_connected && (
            <Chip label={t('tools.configured')} size="small" color="info" sx={{ fontSize: '0.7rem' }} />
          )}
        </Box>

        <Accordion sx={{ mt: 1, '&:before': { display: 'none' }, boxShadow: 'none', bgcolor: 'transparent' }}>
          <AccordionSummary expandIcon={<ExpandMore />} sx={{ px: 0, minHeight: 32, '& .MuiAccordionSummary-content': { my: 0.5 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Code fontSize="small" />
              <Typography variant="body2" fontWeight={500}>{t('tools.actions')}</Typography>
              <Chip label={connector.actions.length} size="small" color="primary" sx={{ height: 20, fontSize: '0.65rem' }} />
            </Box>
          </AccordionSummary>
          <AccordionDetails sx={{ px: 0 }}>
            <List dense disablePadding>
              {connector.actions.map(action => (
                <ListItem key={action.name} sx={{ px: 1, py: 0.5, borderRadius: 1, bgcolor: alpha(theme.palette.primary.main, 0.04), mb: 0.5 }}>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Typography variant="body2" fontWeight={600} fontFamily="monospace">{action.name}</Typography>
                        <Chip label={`${action.input_schema?.length || 0} params`} size="small" sx={{ height: 18, fontSize: '0.6rem' }} />
                      </Box>
                    }
                    secondary={action.description}
                    secondaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      </CardContent>
    </Card>
  );
};

/* ── Main Page ── */
const ToolsConfigPage: React.FC = () => {
  const { t } = useTranslation();
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const [subTab, setSubTab] = useState(0);
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [enabledConfig, setEnabledConfig] = useState<EnabledConfig>(loadConfig);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [toolsRes, connectorsRes] = await Promise.all([
        api.get('/api/tools').catch(() => ({ data: [] })),
        api.get('/api/connectors').catch(() => ({ data: [] })),
      ]);
      setTools(toolsRes.data);
      setConnectors(connectorsRes.data);
    } catch (e: any) {
      enqueueSnackbar(t('common.error'), { variant: 'error' });
    }
    setLoading(false);
  }, [enqueueSnackbar, t]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleToggle = (slug: string, enabled: boolean) => {
    const updated = { ...enabledConfig, [slug]: enabled };
    setEnabledConfig(updated);
    saveConfig(updated);
    enqueueSnackbar(
      enabled ? t('tools.enabled', { name: slug }) : t('tools.disabled', { name: slug }),
      { variant: 'info', autoHideDuration: 1500 }
    );
  };

  const isEnabled = (slug: string) => enabledConfig[slug] !== false;

  const filteredTools = tools.filter(t =>
    !search || t.name.toLowerCase().includes(search.toLowerCase()) ||
    t.slug.toLowerCase().includes(search.toLowerCase()) ||
    t.category.toLowerCase().includes(search.toLowerCase())
  );

  const filteredConnectors = connectors.filter(c =>
    !search || c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.slug.toLowerCase().includes(search.toLowerCase()) ||
    c.category.toLowerCase().includes(search.toLowerCase())
  );

  const toolCategories = Array.from(new Set(tools.map(t => t.category))).sort();
  const connectorCategories = Array.from(new Set(connectors.map(c => c.category))).sort();

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Typography variant="h5" fontWeight={700}>{t('tools.title')}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {tools.length} {t('tools.tools')} &middot; {connectors.length} {t('tools.connectors')}
          </Typography>
        </Box>
        <Tooltip title={t('tools.refresh')}>
          <IconButton onClick={fetchData} disabled={loading}>
            <Refresh />
          </IconButton>
        </Tooltip>
      </Box>

      <Box sx={{ display: 'flex', gap: 2, mb: 3, alignItems: 'center' }}>
        <TextField
          size="small"
          placeholder={t('common.search')}
          value={search}
          onChange={e => setSearch(e.target.value)}
          InputProps={{
            startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment>,
          }}
          sx={{ minWidth: 280 }}
        />
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs
          value={subTab}
          onChange={(_, v) => setSubTab(v)}
          sx={{
            '& .MuiTab-root': { textTransform: 'none', fontWeight: 600, fontSize: '0.85rem', minHeight: 40 },
            '& .MuiTabs-indicator': { height: 3, borderRadius: '3px 3px 0 0' },
          }}
        >
          <Tab
            icon={<Build fontSize="small" />}
            iconPosition="start"
            label={`${t('tools.tools')} (${tools.length})`}
          />
          <Tab
            icon={<Extension fontSize="small" />}
            iconPosition="start"
            label={`${t('tools.connectors')} (${connectors.length})`}
          />
        </Tabs>
      </Box>

      {/* Tools Tab */}
      {subTab === 0 && (
        <>
          {filteredTools.length === 0 && !loading && (
            <Alert severity="info" sx={{ mb: 3, borderRadius: 2 }}>
              {t('tools.noToolsFound')}
            </Alert>
          )}
          {toolCategories.map(cat => {
            const catTools = filteredTools.filter(t => t.category === cat);
            if (catTools.length === 0) return null;
            return (
              <Box key={cat} sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <Category fontSize="small" sx={{ color: 'text.secondary' }} />
                  <Typography variant="subtitle2" fontWeight={700} textTransform="uppercase" color="text.secondary" letterSpacing={1}>
                    {cat}
                  </Typography>
                  <Chip label={catTools.length} size="small" sx={{ height: 20, fontSize: '0.7rem' }} />
                </Box>
                <Grid container spacing={2.5}>
                  {catTools.map(tool => (
                    <Grid item xs={12} md={6} lg={4} key={tool.slug}>
                      <ToolCard tool={tool} enabled={isEnabled(tool.slug)} onToggle={handleToggle} />
                    </Grid>
                  ))}
                </Grid>
              </Box>
            );
          })}
        </>
      )}

      {/* Connectors Tab */}
      {subTab === 1 && (
        <>
          {filteredConnectors.length === 0 && !loading && (
            <Alert severity="info" sx={{ mb: 3, borderRadius: 2 }}>
              {t('tools.noConnectorsFound')}
            </Alert>
          )}
          {connectorCategories.map(cat => {
            const catConnectors = filteredConnectors.filter(c => c.category === cat);
            if (catConnectors.length === 0) return null;
            return (
              <Box key={cat} sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <Category fontSize="small" sx={{ color: 'text.secondary' }} />
                  <Typography variant="subtitle2" fontWeight={700} textTransform="uppercase" color="text.secondary" letterSpacing={1}>
                    {cat}
                  </Typography>
                  <Chip label={catConnectors.length} size="small" sx={{ height: 20, fontSize: '0.7rem' }} />
                </Box>
                <Grid container spacing={2.5}>
                  {catConnectors.map(connector => (
                    <Grid item xs={12} md={6} lg={4} key={connector.slug}>
                      <ConnectorCard connector={connector} enabled={isEnabled(connector.slug)} onToggle={handleToggle} />
                    </Grid>
                  ))}
                </Grid>
              </Box>
            );
          })}
        </>
      )}
    </Box>
  );
};

export default ToolsConfigPage;
