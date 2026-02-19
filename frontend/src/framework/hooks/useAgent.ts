/**
 * useAgent — Hook principal pour interagir avec un agent.
 *
 * Gère:
 * - Envoi de messages (async ou sync)
 * - Réception des réponses et streaming
 * - Historique de conversation (auto-restauré depuis le backend)
 * - État de chargement et progression
 * - Workspace collaboratif (optionnel)
 *
 * Usage dans un composant agent:
 *   const { sendMessage, messages, isLoading, streamingContent } = useAgent('mon-agent', sessionId);
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { ChatMessage, JobInfo, StreamChunk } from 'framework/types';

const API_BASE = process.env.REACT_APP_API_URL || '';

interface UseAgentOptions {
  /** Mode synchrone (attend la réponse) ou async (job en background) */
  mode?: 'sync' | 'async';
  /** ID du workspace (mode collaboratif) */
  workspaceId?: string | null;
}

interface UseAgentReturn {
  /** Envoyer un message à l'agent */
  sendMessage: (content: string, metadata?: Record<string, unknown>) => Promise<void>;
  /** Historique des messages */
  messages: ChatMessage[];
  /** Agent en cours de traitement */
  isLoading: boolean;
  /** Contenu en cours de streaming */
  streamingContent: string;
  /** Progression du job (0-100) */
  progress: number;
  /** Message de progression */
  progressMessage: string;
  /** Erreur éventuelle */
  error: string | null;
  /** Effacer l'historique local */
  clearMessages: () => void;
  /** Charger une session existante */
  loadSession: (sessionId: string) => Promise<void>;
  /** Session restaurée depuis le backend */
  sessionRestored: boolean;
}

export function useAgent(
  agentSlug: string,
  sessionId: string,
  options: UseAgentOptions = {}
): UseAgentReturn {
  const { mode = 'sync', workspaceId } = options;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [sessionRestored, setSessionRestored] = useState(false);
  const restoreAttempted = useRef(false);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    };
  };

  // Auto-restore session messages from backend on mount
  useEffect(() => {
    if (!sessionId || restoreAttempted.current) return;
    restoreAttempted.current = true;

    const restore = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/api/agent-runtime/sessions/${sessionId}`,
          { headers: getAuthHeaders() }
        );

        if (response.ok) {
          const session = await response.json();
          if (session.messages && session.messages.length > 0) {
            setMessages(session.messages);
          }
        }
        // 404 = new session, that's fine
      } catch {
        // Silently fail — new session
      } finally {
        setSessionRestored(true);
      }
    };

    restore();
  }, [sessionId]);

  const sendMessage = useCallback(
    async (content: string, metadata?: Record<string, unknown>) => {
      setError(null);
      setIsLoading(true);
      setStreamingContent('');
      setProgress(0);

      // Ajouter le message utilisateur à l'historique local
      const userMessage: ChatMessage = {
        role: 'user',
        content,
        attachments: [],
        metadata: metadata || {},
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      try {
        if (mode === 'sync') {
          // Appel synchrone — attend la réponse complète
          const response = await fetch(
            `${API_BASE}/api/agent-runtime/${agentSlug}/chat/sync`,
            {
              method: 'POST',
              headers: getAuthHeaders(),
              body: JSON.stringify({
                message: content,
                session_id: sessionId,
                metadata: metadata || {},
                workspace_id: workspaceId || undefined,
              }),
            }
          );

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail?.error || 'Erreur de l\'agent');
          }

          const data = await response.json();

          const assistantMessage: ChatMessage = {
            role: 'assistant',
            content: data.content,
            attachments: data.attachments || [],
            metadata: data.metadata || {},
            timestamp: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMessage]);
        } else {
          // Appel async — crée un job
          const response = await fetch(
            `${API_BASE}/api/agent-runtime/${agentSlug}/chat`,
            {
              method: 'POST',
              headers: getAuthHeaders(),
              body: JSON.stringify({
                message: content,
                session_id: sessionId,
                metadata: metadata || {},
                stream: true,
                workspace_id: workspaceId || undefined,
              }),
            }
          );

          if (!response.ok) throw new Error('Erreur de création du job');

          const { job_id } = await response.json();

          // Polling du job (en attendant l'intégration WebSocket complète)
          await pollJob(job_id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur inconnue');
      } finally {
        setIsLoading(false);
        setStreamingContent('');
        setProgress(0);
      }
    },
    [agentSlug, sessionId, mode, workspaceId]
  );

  const pollJob = async (jobId: string) => {
    const maxAttempts = 120; // 2 minutes max
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise((resolve) => setTimeout(resolve, 1000));

      const response = await fetch(`${API_BASE}/api/agent-runtime/jobs/${jobId}`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) continue;

      const job: JobInfo = await response.json();
      setProgress(job.progress);
      setProgressMessage(job.progress_message);

      if (job.status === 'completed' && job.result) {
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: job.result.content,
          attachments: job.result.attachments || [],
          metadata: job.result.metadata || {},
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
        return;
      }

      if (job.status === 'failed') {
        throw new Error(job.error || 'Le job a échoué');
      }
    }

    throw new Error('Timeout: le job n\'a pas terminé dans les 2 minutes');
  };

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const loadSession = useCallback(
    async (sid: string) => {
      try {
        const response = await fetch(`${API_BASE}/api/agent-runtime/sessions/${sid}`, {
          headers: getAuthHeaders(),
        });

        if (!response.ok) throw new Error('Session introuvable');

        const session = await response.json();
        setMessages(session.messages || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur de chargement');
      }
    },
    []
  );

  return {
    sendMessage,
    messages,
    isLoading,
    streamingContent,
    progress,
    progressMessage,
    error,
    clearMessages,
    loadSession,
    sessionRestored,
  };
}
