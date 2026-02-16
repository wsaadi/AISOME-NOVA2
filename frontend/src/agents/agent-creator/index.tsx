/**
 * Agent Creator View — Interactive interface for creating NOVA2 agents.
 *
 * Layout:
 *  - Header with agent name badge when generated
 *  - Progress bar during LLM processing
 *  - Full-width chat panel
 *  - Results panel when files are generated:
 *    - Validation status (pass/fail with details)
 *    - File list with expandable preview
 *    - Download ZIP button
 */

import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AgentViewProps, ChatMessage } from 'framework/types';
import { ChatPanel, ActionButton, MarkdownView } from 'framework/components';
import { useAgent } from 'framework/hooks';
import styles from './styles';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Extract generated files from the latest assistant message metadata. */
const extractGenerated = (
  messages: ChatMessage[]
): {
  files: Record<string, string>;
  slug: string;
  validation: { valid?: boolean; errors?: string[]; warnings?: string[] };
} | null => {
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (
      msg.role === 'assistant' &&
      msg.metadata?.phase === 'generated' &&
      msg.metadata?.files
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

/** CRC-32 lookup table (IEEE 802.3). */
const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[i] = c;
  }
  return t;
})();

const crc32 = (data: Uint8Array): number => {
  let crc = 0xffffffff;
  for (let i = 0; i < data.length; i++) crc = CRC_TABLE[(crc ^ data[i]) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
};

/** Build a valid ZIP blob from a map of filepath → content. */
const buildZip = (files: Record<string, string>): Blob => {
  const enc = new TextEncoder();
  const entries: { name: Uint8Array; data: Uint8Array; crc: number; offset: number }[] = [];
  const parts: Uint8Array[] = [];
  let offset = 0;

  for (const [path, content] of Object.entries(files)) {
    const nameBytes = enc.encode(path);
    const dataBytes = enc.encode(content);
    const fileCrc = crc32(dataBytes);

    const header = new ArrayBuffer(30);
    const v = new DataView(header);
    v.setUint32(0, 0x04034b50, true);
    v.setUint16(4, 20, true);
    v.setUint16(8, 0, true);
    v.setUint32(14, fileCrc, true);
    v.setUint32(18, dataBytes.length, true);
    v.setUint32(22, dataBytes.length, true);
    v.setUint16(26, nameBytes.length, true);
    v.setUint16(28, 0, true);

    const h = new Uint8Array(header);
    parts.push(h, nameBytes, dataBytes);
    entries.push({ name: nameBytes, data: dataBytes, crc: fileCrc, offset });
    offset += h.length + nameBytes.length + dataBytes.length;
  }

  const cdStart = offset;
  for (const e of entries) {
    const cd = new ArrayBuffer(46);
    const cv = new DataView(cd);
    cv.setUint32(0, 0x02014b50, true);
    cv.setUint16(4, 20, true);
    cv.setUint16(6, 20, true);
    cv.setUint32(16, e.crc, true);
    cv.setUint32(20, e.data.length, true);
    cv.setUint32(24, e.data.length, true);
    cv.setUint16(28, e.name.length, true);
    cv.setUint32(42, e.offset, true);

    const c = new Uint8Array(cd);
    parts.push(c, e.name);
    offset += c.length + e.name.length;
  }

  const eocd = new ArrayBuffer(22);
  const ev = new DataView(eocd);
  ev.setUint32(0, 0x06054b50, true);
  ev.setUint16(8, entries.length, true);
  ev.setUint16(10, entries.length, true);
  ev.setUint32(12, offset - cdStart, true);
  ev.setUint32(16, cdStart, true);
  parts.push(new Uint8Array(eocd));

  return new Blob(parts, { type: 'application/zip' });
};

/** Get the appropriate language tag for a file path (for syntax highlighting). */
const langForFile = (path: string): string => {
  if (path.endsWith('.py')) return 'python';
  if (path.endsWith('.tsx') || path.endsWith('.ts')) return 'typescript';
  if (path.endsWith('.json')) return 'json';
  if (path.endsWith('.md')) return 'markdown';
  return '';
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const AgentCreatorView: React.FC<AgentViewProps> = ({ agent, sessionId }) => {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const editSlug = searchParams.get('edit');

  const {
    sendMessage,
    messages,
    isLoading,
    streamingContent,
    progress,
    progressMessage,
    error,
  } = useAgent(agent.slug, sessionId);

  // Edit mode: send initial context on first render
  const editInitSent = useRef(false);
  useEffect(() => {
    if (!editSlug || editInitSent.current || messages.length > 0) return;
    editInitSent.current = true;
    // Send initial edit request with metadata
    sendMessage(
      t('agentCreator.editInitMessage', 'I want to modify the agent "{{slug}}". What changes would you like me to make?').replace('{{slug}}', editSlug),
      { edit_mode: true, edit_agent_slug: editSlug },
    );
  }, [editSlug, messages.length, sendMessage, t]);

  // Wrap sendMessage to always include edit metadata when in edit mode
  const sendMessageWrapped = useCallback(
    (content: string, metadata?: Record<string, unknown>) => {
      const meta = { ...metadata };
      if (editSlug) {
        meta.edit_mode = true;
        meta.edit_agent_slug = editSlug;
      }
      return sendMessage(content, meta);
    },
    [sendMessage, editSlug],
  );

  // Track which files are expanded in the preview
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
  const [deployStatus, setDeployStatus] = useState<'idle' | 'deploying' | 'success' | 'error'>('idle');
  const [deployMessage, setDeployMessage] = useState('');

  // Extract generated files from conversation
  const generated = useMemo(() => extractGenerated(messages), [messages]);
  const hasFiles = generated !== null && Object.keys(generated.files).length > 0;

  const isValid = generated?.validation?.valid === true;
  const validationErrors = generated?.validation?.errors || [];
  const validationWarnings = generated?.validation?.warnings || [];

  const toggleFile = useCallback((path: string) => {
    setExpandedFiles((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    if (!generated) return;
    setExpandedFiles(new Set(Object.keys(generated.files)));
  }, [generated]);

  const collapseAll = useCallback(() => {
    setExpandedFiles(new Set());
  }, []);

  const handleDownloadZip = useCallback(() => {
    if (!generated) return;
    const blob = buildZip(generated.files);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${generated.slug}.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [generated]);

  const handleDeploy = useCallback(async () => {
    if (!generated) return;
    setDeployStatus('deploying');
    setDeployMessage('');

    try {
      const blob = buildZip(generated.files);
      const formData = new FormData();
      formData.append('file', blob, `${generated.slug}.zip`);

      const token = localStorage.getItem('access_token');
      const API_BASE = process.env.REACT_APP_API_URL || '';
      // In edit mode, pass overwrite param to update existing agent
      const overwriteParam = editSlug ? `?overwrite=${encodeURIComponent(editSlug)}` : '';
      const response = await fetch(`${API_BASE}/api/agents/import${overwriteParam}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errData.detail || `Import failed (${response.status})`);
      }

      const data = await response.json();
      setDeployStatus('success');
      setDeployMessage(
        editSlug
          ? t('agentCreator.updateSuccess', 'Agent "{{name}}" updated successfully!').replace('{{name}}', data.name)
          : t('agentCreator.deploySuccess', 'Agent "{{name}}" deployed! Open it from the catalog.').replace('{{name}}', data.name)
      );
    } catch (err) {
      setDeployStatus('error');
      setDeployMessage(err instanceof Error ? err.message : 'Deploy failed');
    }
  }, [generated, editSlug, t]);

  // Sort files for display: agent.json last, others alphabetically
  const sortedFiles = useMemo(() => {
    if (!generated) return [];
    return Object.keys(generated.files).sort((a, b) => {
      if (a === 'agent.json') return 1;
      if (b === 'agent.json') return -1;
      return a.localeCompare(b);
    });
  }, [generated]);

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.headerIcon}>{editSlug ? '✏️' : '✨'}</span>
          <h3 style={styles.headerTitle}>
            {editSlug
              ? t('agentCreator.editTitle', 'Edit Agent')
              : t('agentCreator.title', 'Agent Creator')}
          </h3>
          {editSlug && <span style={styles.editBadge}>{editSlug}</span>}
          {generated && <span style={styles.slugBadge}>{generated.slug}</span>}
        </div>
      </div>

      {/* Progress bar */}
      {isLoading && progress > 0 && (
        <div style={styles.progressBar}>
          <div style={styles.progressTrack}>
            <div style={{ ...styles.progressFill, width: `${progress}%` }} />
          </div>
          <span style={styles.progressText}>{progressMessage || `${progress}%`}</span>
        </div>
      )}

      {/* Error */}
      {error && <div style={styles.errorBanner}>{error}</div>}

      {/* Results panel when files are generated */}
      {hasFiles && generated && (
        <div style={styles.resultsPanel}>
          {/* Validation status */}
          <div style={styles.validationRow}>
            <span style={isValid ? styles.validationPass : styles.validationFail}>
              {isValid
                ? (t('agentCreator.validationPassed', 'Validation passed'))
                : `${validationErrors.length} ${t('agentCreator.errors', 'error(s)')}`}
            </span>
            {validationWarnings.length > 0 && (
              <span style={styles.validationWarn}>
                {validationWarnings.length} {t('agentCreator.warnings', 'warning(s)')}
              </span>
            )}
            <div style={styles.spacer} />
            <span style={styles.fileCount}>
              {Object.keys(generated.files).length} {t('agentCreator.filesGenerated', 'files')}
            </span>
          </div>

          {/* Validation errors detail */}
          {validationErrors.length > 0 && (
            <div style={styles.validationDetail}>
              {validationErrors.map((err, i) => (
                <div key={i} style={styles.validationErrorItem}>{err}</div>
              ))}
            </div>
          )}

          {/* File list with expand/collapse */}
          <div style={styles.fileListHeader}>
            <span style={styles.fileListTitle}>{t('agentCreator.generatedFiles', 'Generated files')}</span>
            <div style={styles.fileListActions}>
              <span style={styles.linkBtn} onClick={expandAll}>
                {t('agentCreator.expandAll', 'Expand all')}
              </span>
              <span style={styles.linkBtn} onClick={collapseAll}>
                {t('agentCreator.collapseAll', 'Collapse all')}
              </span>
            </div>
          </div>

          <div style={styles.fileList}>
            {sortedFiles.map((path) => (
              <div key={path} style={styles.fileItem}>
                <div style={styles.fileItemHeader} onClick={() => toggleFile(path)}>
                  <span style={styles.fileToggle}>{expandedFiles.has(path) ? '▼' : '▶'}</span>
                  <span style={styles.fileName}>{path}</span>
                </div>
                {expandedFiles.has(path) && (
                  <div style={styles.filePreview}>
                    <MarkdownView
                      content={`\`\`\`${langForFile(path)}\n${generated.files[path]}\n\`\`\``}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Deploy + Download buttons */}
          <div style={styles.downloadRow}>
            <ActionButton
              label={
                deployStatus === 'deploying'
                  ? t('agentCreator.deploying', 'Deploying...')
                  : editSlug
                    ? t('agentCreator.update', 'Update agent')
                    : t('agentCreator.deploy', 'Deploy to platform')
              }
              onClick={handleDeploy}
              loading={deployStatus === 'deploying'}
              disabled={deployStatus === 'deploying'}
            />
            <ActionButton
              label={`${t('agentCreator.downloadZip', 'Download ZIP')} (${generated.slug}.zip)`}
              onClick={handleDownloadZip}
            />
          </div>
          {deployMessage && (
            <div style={{
              ...styles.deployMessage,
              color: deployStatus === 'success' ? '#2e7d32' : '#d32f2f',
            }}>
              {deployMessage}
            </div>
          )}
        </div>
      )}

      {/* Chat */}
      <div style={styles.chatArea}>
        <ChatPanel
          messages={messages}
          onSendMessage={sendMessageWrapped}
          isLoading={isLoading}
          streamingContent={streamingContent}
          placeholder={
            editSlug
              ? t('agentCreator.editPlaceholder', 'Describe the changes you want to make...')
              : t('agentCreator.placeholder', 'Describe the agent you want to create...')
          }
        />
      </div>
    </div>
  );
};

export default AgentCreatorView;
