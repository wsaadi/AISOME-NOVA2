/**
 * Agent Creator View — Interface for creating NOVA2 agents via natural language.
 *
 * Layout:
 * - Split view: Chat on the left, generated files preview on the right
 * - When no files are generated yet, chat takes full width
 * - File tabs allow switching between generated files
 * - Validation status shown in the files panel
 * - Action buttons for deployment
 */

import React, { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { AgentViewProps, ChatMessage } from 'framework/types';
import { ChatPanel, MarkdownView, ActionButton } from 'framework/components';
import { useAgent, useAgentStorage } from 'framework/hooks';
import styles from './styles';

/**
 * Maps file paths to display-friendly short names.
 */
const getFileLabel = (filepath: string): string => {
  const parts = filepath.split('/');
  return parts[parts.length - 1];
};

/**
 * Detects the language for syntax highlighting from file extension.
 */
const getLanguage = (filepath: string): string => {
  if (filepath.endsWith('.json')) return 'json';
  if (filepath.endsWith('.py')) return 'python';
  if (filepath.endsWith('.md')) return 'markdown';
  if (filepath.endsWith('.tsx') || filepath.endsWith('.ts')) return 'typescript';
  return 'text';
};

/**
 * Extracts generated files from the most recent assistant message metadata.
 */
const extractFilesFromMessages = (
  messages: ChatMessage[]
): { files: Record<string, string>; slug: string; validation: Record<string, unknown> } | null => {
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (
      msg.role === 'assistant' &&
      msg.metadata &&
      msg.metadata.phase === 'generated' &&
      msg.metadata.files
    ) {
      return {
        files: msg.metadata.files as Record<string, string>,
        slug: (msg.metadata.agent_slug as string) || 'unknown',
        validation: (msg.metadata.validation as Record<string, unknown>) || {},
      };
    }
  }
  return null;
};

const AgentCreatorView: React.FC<AgentViewProps> = ({ agent, sessionId, userId }) => {
  const { t } = useTranslation();
  const {
    sendMessage,
    messages,
    isLoading,
    streamingContent,
    progress,
    progressMessage,
    error,
  } = useAgent(agent.slug, sessionId);

  const { download } = useAgentStorage(agent.slug);

  const [activeFileTab, setActiveFileTab] = useState<string>('');

  // Extract generated files from conversation
  const generated = useMemo(() => extractFilesFromMessages(messages), [messages]);

  const fileKeys = useMemo(() => {
    if (!generated) return [];
    return Object.keys(generated.files);
  }, [generated]);

  // Auto-select first file tab when files appear
  const currentTab = useMemo(() => {
    if (activeFileTab && fileKeys.includes(activeFileTab)) return activeFileTab;
    return fileKeys.length > 0 ? fileKeys[0] : '';
  }, [activeFileTab, fileKeys]);

  const hasFiles = fileKeys.length > 0;

  /**
   * Handle downloading all generated files as individual downloads.
   */
  const handleDownload = useCallback(async () => {
    if (!generated) return;
    for (const [filepath, content] of Object.entries(generated.files)) {
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = getFileLabel(filepath);
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  }, [generated]);

  /**
   * Copy current file content to clipboard.
   */
  const handleCopyFile = useCallback(() => {
    if (!generated || !currentTab) return;
    const content = generated.files[currentTab];
    if (content) {
      navigator.clipboard.writeText(content);
    }
  }, [generated, currentTab]);

  const validation = generated?.validation || {};
  const isValid = validation.valid === true;
  const validationErrors = (validation.errors as string[]) || [];
  const validationWarnings = (validation.warnings as string[]) || [];

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h3 style={styles.headerTitle}>
          {t('agentCreator.title')}
          {generated && (
            <span style={styles.headerBadge}>
              {generated.slug}
            </span>
          )}
        </h3>
        {hasFiles && (
          <div style={{ display: 'flex', gap: 8 }}>
            <ActionButton
              label={t('agentCreator.copy')}
              onClick={handleCopyFile}
            />
            <ActionButton
              label={t('agentCreator.download')}
              onClick={handleDownload}
            />
          </div>
        )}
      </div>

      {/* Progress bar */}
      {isLoading && progress > 0 && (
        <div style={styles.progressBar}>
          <div style={styles.progressTrack}>
            <div style={{ ...styles.progressFill, width: `${progress}%` }} />
          </div>
          <span>{progressMessage || `${progress}%`}</span>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div style={{ padding: '8px 16px', color: 'var(--error-color, #d32f2f)', fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* Main body: chat + files */}
      <div style={styles.body}>
        {/* Chat panel */}
        <div style={hasFiles ? styles.chatPanelWithFiles : styles.chatPanel}>
          <ChatPanel
            messages={messages}
            onSendMessage={sendMessage}
            isLoading={isLoading}
            streamingContent={streamingContent}
            placeholder={t('agentCreator.placeholder')}
          />
        </div>

        {/* Generated files panel */}
        {hasFiles && generated && (
          <div style={styles.filesPanel}>
            {/* File tabs */}
            <div style={styles.filesTabs}>
              {fileKeys.map((filepath) => (
                <button
                  key={filepath}
                  style={filepath === currentTab ? styles.fileTabActive : styles.fileTab}
                  onClick={() => setActiveFileTab(filepath)}
                >
                  {getFileLabel(filepath)}
                </button>
              ))}
            </div>

            {/* Validation status */}
            <div style={styles.validationBar}>
              {isValid ? (
                <span style={styles.validationSuccess}>
                  {t('agentCreator.validationPassed')}
                </span>
              ) : (
                <span style={styles.validationError}>
                  {validationErrors.length} {t('agentCreator.errors')}
                  {validationWarnings.length > 0 && `, ${validationWarnings.length} ${t('agentCreator.warnings')}`}
                </span>
              )}
            </div>

            {/* File content */}
            <div style={styles.fileContent}>
              {currentTab && generated.files[currentTab] ? (
                <MarkdownView
                  content={`\`\`\`${getLanguage(currentTab)}\n${generated.files[currentTab]}\n\`\`\``}
                />
              ) : (
                <div style={styles.emptyFiles}>
                  <span>{t('agentCreator.selectFile')}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentCreatorView;
