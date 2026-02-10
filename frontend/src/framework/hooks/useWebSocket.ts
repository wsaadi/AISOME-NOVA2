/**
 * useWebSocket — Hook de connexion WebSocket pour le temps réel.
 *
 * Gère automatiquement:
 * - Connexion/déconnexion
 * - Reconnexion automatique
 * - Dispatch des messages (job updates, stream chunks)
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { WebSocketMessage } from '@framework/types';

interface UseWebSocketOptions {
  /** URL du WebSocket (défaut: auto-détecté) */
  url?: string;
  /** Token d'authentification */
  token: string;
  /** Callback pour les messages reçus */
  onMessage?: (message: WebSocketMessage) => void;
  /** Reconnexion automatique */
  autoReconnect?: boolean;
  /** Délai max de reconnexion en ms */
  maxReconnectDelay?: number;
}

interface UseWebSocketReturn {
  /** État de la connexion */
  isConnected: boolean;
  /** Envoyer un message */
  sendMessage: (data: Record<string, unknown>) => void;
  /** Forcer la reconnexion */
  reconnect: () => void;
}

export function useWebSocket({
  url,
  token,
  onMessage,
  autoReconnect = true,
  maxReconnectDelay = 30000,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout>>();

  const wsUrl = url || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws?token=${token}`;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      reconnectAttempt.current = 0;
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;

      if (autoReconnect) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempt.current), maxReconnectDelay);
        reconnectAttempt.current += 1;
        reconnectTimeout.current = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WebSocketMessage;
        onMessage?.(data);
      } catch {
        // Ignore malformed messages
      }
    };

    wsRef.current = ws;
  }, [wsUrl, onMessage, autoReconnect, maxReconnectDelay]);

  const sendMessage = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const reconnect = useCallback(() => {
    wsRef.current?.close();
    reconnectAttempt.current = 0;
    connect();
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { isConnected, sendMessage, reconnect };
}
