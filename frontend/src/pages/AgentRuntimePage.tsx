/**
 * AgentRuntimePage — Dynamic loader for agent views.
 *
 * Routes: /agent/:slug
 *
 * This page:
 * 1. Reads the agent slug from the URL
 * 2. Fetches agent metadata from the backend
 * 3. Checks the agent registry for a custom frontend view
 * 4. Renders the custom view or falls back to a default chat interface
 * 5. Manages session ID generation and persistence
 */

import React, { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Box, Typography, CircularProgress, Paper, IconButton, Tooltip, alpha, useTheme,
  Button,
} from '@mui/material';
import { ArrowBack, CloudUpload } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import agentViews from '../agents/registry';
import { AgentManifest } from 'framework/types';
import { ChatPanel } from 'framework/components';
import { useAgent, useAgentStorage } from 'framework/hooks';

/**
 * Generate a unique session ID for this agent session.
 * Uses a combination of agent slug and timestamp to ensure uniqueness.
 */
const generateSessionId = (slug: string): string => {
  const random = Math.random().toString(36).substring(2, 10);
  const ts = Date.now().toString(36);
  return `${slug}-${ts}-${random}`;
};

/**
 * Get or create a session ID from sessionStorage.
 * Persists across page reloads but not across tabs.
 */
const getSessionId = (slug: string): string => {
  const key = `agent_session_${slug}`;
  let sessionId = sessionStorage.getItem(key);
  if (!sessionId) {
    sessionId = generateSessionId(slug);
    sessionStorage.setItem(key, sessionId);
  }
  return sessionId;
};

/**
 * Default Chat View — Used when an agent has no custom frontend.
 *
 * When the agent declares 'file_upload' in capabilities, a drop-zone /
 * upload button is rendered above the chat panel so users can attach
 * files for analysis (PDF, DOCX, etc.).
 */
const DefaultAgentView: React.FC<{ agent: AgentManifest; sessionId: string }> = ({ agent, sessionId }) => {
  const { sendMessage, messages, isLoading, streamingContent, progress, progressMessage } = useAgent(agent.slug, sessionId);
  const storage = useAgentStorage(agent.slug);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const hasFileUpload = agent.capabilities?.includes('file_upload');

  // Determine accepted file types from triggers config
  const acceptTypes = React.useMemo(() => {
    const trigger = agent.triggers?.find((t) => t.type === 'file_upload');
    const accept = (trigger?.config as any)?.accept;
    return Array.isArray(accept) ? accept.join(',') : '.pdf,.docx,.doc,.txt';
  }, [agent.triggers]);

  const handleFileUpload = React.useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const key = await storage.upload(file);
      await sendMessage(`Analyser le fichier: ${file.name}`, {
        fileKey: key,
        fileName: file.name,
      });
    } catch {
      // Error is handled by the hook's error state
    }
    // Reset input so the same file can be re-uploaded
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, [storage, sendMessage]);

  return (
    <Box sx={{ height: 'calc(100vh - 180px)', display: 'flex', flexDirection: 'column' }}>
      {/* File upload area for agents with file_upload capability */}
      {hasFileUpload && (
        <Box sx={{
          p: 1.5, px: 2,
          borderBottom: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          bgcolor: 'action.hover',
        }}>
          <input
            ref={fileInputRef}
            type="file"
            accept={acceptTypes}
            style={{ display: 'none' }}
            onChange={handleFileUpload}
          />
          <Button
            variant="outlined"
            size="small"
            startIcon={<CloudUpload />}
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading || storage.isUploading}
          >
            {storage.isUploading ? 'Upload...' : 'Uploader un fichier'}
          </Button>
          <Typography variant="caption" color="text.secondary">
            {acceptTypes.replace(/\./g, '').toUpperCase()}
          </Typography>
        </Box>
      )}

      {/* Progress indicator */}
      {isLoading && progress > 0 && (
        <Box sx={{ px: 2, py: 0.5, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary">
            {progressMessage || `${progress}%`}
          </Typography>
          <Box sx={{ height: 2, bgcolor: 'divider', borderRadius: 1, overflow: 'hidden', mt: 0.5 }}>
            <Box sx={{ height: '100%', bgcolor: 'primary.main', width: `${progress}%`, transition: 'width 0.3s' }} />
          </Box>
        </Box>
      )}

      <ChatPanel
        messages={messages}
        onSendMessage={sendMessage}
        isLoading={isLoading}
        streamingContent={streamingContent}
      />
    </Box>
  );
};

const AgentRuntimePage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [searchParams] = useSearchParams();
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const theme = useTheme();

  const [agent, setAgent] = useState<AgentManifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Include edit param in session key so editing gets its own session
  const editSlug = searchParams.get('edit');
  const sessionKey = editSlug ? `${slug}-edit-${editSlug}` : slug;
  const sessionId = useMemo(() => sessionKey ? getSessionId(sessionKey) : '', [sessionKey]);

  const fetchAgent = useCallback(async () => {
    if (!slug) return;
    setLoading(true);
    setError(null);

    try {
      // Try the runtime catalog first (filesystem-based agents)
      const catalogRes = await api.get('/api/agent-runtime/catalog');
      const agents: AgentManifest[] = catalogRes.data;
      const found = agents.find((a: AgentManifest) => a.slug === slug);

      if (found) {
        setAgent(found);
      } else {
        // Fallback: try the DB-based agents endpoint
        const dbRes = await api.get('/api/agents');
        const dbAgent = dbRes.data.find((a: any) => a.slug === slug);
        if (dbAgent) {
          const cfg = dbAgent.config || {};
          const agentData: any = {
            name: dbAgent.name,
            slug: dbAgent.slug,
            version: dbAgent.version || '1.0.0',
            description: dbAgent.description || '',
            author: '',
            icon: cfg.icon || 'smart_toy',
            category: cfg.category || dbAgent.agent_type || 'general',
            tags: cfg.tags || [],
            dependencies: cfg.dependencies || { tools: [], connectors: [] },
            triggers: cfg.triggers || [{ type: 'user_message', config: {} }],
            capabilities: cfg.capabilities || [],
            min_platform_version: '1.0.0',
          };
          // For n8n_workflow agents, include the full config so the dynamic
          // renderer can access workflow_analysis, n8n_workflow_id, etc.
          if (dbAgent.agent_type === 'n8n_workflow') {
            agentData.agent_type = 'n8n_workflow';
            agentData.config = cfg;
          }
          setAgent(agentData);
        } else {
          setError(t('agents.notFound') || `Agent "${slug}" not found`);
        }
      }
    } catch {
      setError(t('common.error') || 'Failed to load agent');
    } finally {
      setLoading(false);
    }
  }, [slug, t]);

  useEffect(() => { fetchAgent(); }, [fetchAgent]);

  // Check if a custom view is registered for this agent.
  // For n8n_workflow agents, use the shared n8n-workflow dynamic renderer
  // which reads workflow_analysis from agent.config to build the appropriate UI.
  const isWorkflowAgent = agent?.category === 'n8n_workflow' || (agent as any)?.agent_type === 'n8n_workflow';
  const viewKey = isWorkflowAgent ? 'n8n-workflow' : slug;
  const CustomView = viewKey ? agentViews[viewKey] : undefined;
  const userId = user?.id ? Number(user.id) : 0;

  if (loading) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '50vh', gap: 2 }}>
        <CircularProgress />
        <Typography color="text.secondary">{t('common.loading')}</Typography>
      </Box>
    );
  }

  if (error || !agent) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Typography variant="h5" color="error" gutterBottom>{error || 'Agent not found'}</Typography>
        <Typography
          variant="body2"
          color="primary"
          sx={{ cursor: 'pointer', textDecoration: 'underline', mt: 2 }}
          onClick={() => navigate('/catalog')}
        >
          {t('nav.catalog')}
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Agent header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <Tooltip title={t('nav.catalog')}>
          <IconButton onClick={() => navigate('/catalog')} size="small">
            <ArrowBack />
          </IconButton>
        </Tooltip>
        <Box>
          <Typography variant="h5" fontWeight={700}>{agent.name}</Typography>
          <Typography variant="body2" color="text.secondary">{agent.description}</Typography>
        </Box>
      </Box>

      {/* Agent view container */}
      <Paper
        elevation={0}
        sx={{
          height: 'calc(100vh - 200px)',
          overflow: 'hidden',
          borderRadius: 3,
          border: `1px solid ${theme.palette.divider}`,
          bgcolor: alpha(theme.palette.background.paper, 0.6),
        }}
      >
        {CustomView ? (
          <Suspense fallback={
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <CircularProgress />
            </Box>
          }>
            <CustomView agent={agent} sessionId={sessionId} userId={userId} />
          </Suspense>
        ) : (
          <DefaultAgentView agent={agent} sessionId={sessionId} />
        )}
      </Paper>
    </Box>
  );
};

export default AgentRuntimePage;
