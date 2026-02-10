/**
 * ChatPanel — Composant de chat complet pour les agents.
 *
 * Fournit:
 * - Zone de messages avec historique scrollable
 * - Input de message avec envoi
 * - Indicateur de chargement
 * - Affichage du streaming en temps réel
 * - Support des pièces jointes (optionnel)
 *
 * Usage dans un agent:
 *   import { ChatPanel } from '@framework/components';
 *
 *   <ChatPanel
 *     messages={messages}
 *     onSendMessage={sendMessage}
 *     isLoading={isLoading}
 *     streamingContent={streamingContent}
 *   />
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Box,
  CircularProgress,
  IconButton,
  Paper,
  TextField,
  Typography,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import { ChatMessage } from '@framework/types';
import { MarkdownView } from './MarkdownView';

interface ChatPanelProps {
  /** Liste des messages de la conversation */
  messages: ChatMessage[];
  /** Callback d'envoi de message */
  onSendMessage: (content: string) => Promise<void>;
  /** Agent en cours de traitement */
  isLoading?: boolean;
  /** Contenu en cours de streaming */
  streamingContent?: string;
  /** Placeholder de l'input */
  placeholder?: string;
  /** Désactiver l'input */
  disabled?: boolean;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  onSendMessage,
  isLoading = false,
  streamingContent = '',
  placeholder = 'Écrivez votre message...',
  disabled = false,
}) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading || disabled) return;
    setInput('');
    await onSendMessage(trimmed);
  }, [input, isLoading, disabled, onSendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Messages */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        {messages.map((msg, index) => (
          <Box
            key={index}
            sx={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <Paper
              elevation={1}
              sx={{
                p: 2,
                maxWidth: '75%',
                bgcolor: msg.role === 'user' ? 'primary.main' : 'background.paper',
                color: msg.role === 'user' ? 'primary.contrastText' : 'text.primary',
                borderRadius: 2,
              }}
            >
              <MarkdownView content={msg.content} />
            </Paper>
          </Box>
        ))}

        {/* Streaming content */}
        {streamingContent && (
          <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
            <Paper elevation={1} sx={{ p: 2, maxWidth: '75%', borderRadius: 2 }}>
              <MarkdownView content={streamingContent} />
            </Paper>
          </Box>
        )}

        {/* Loading indicator */}
        {isLoading && !streamingContent && (
          <Box sx={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'center', gap: 1 }}>
            <CircularProgress size={20} />
            <Typography variant="body2" color="text.secondary">
              L'agent réfléchit...
            </Typography>
          </Box>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Input */}
      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading || disabled}
            size="small"
            variant="outlined"
          />
          <IconButton
            color="primary"
            onClick={handleSend}
            disabled={!input.trim() || isLoading || disabled}
          >
            <SendIcon />
          </IconButton>
        </Box>
      </Box>
    </Box>
  );
};
