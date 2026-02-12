/**
 * Agent Creator View — Interface for creating NOVA2 agents via natural language.
 *
 * Layout:
 * - Full-width chat
 * - When files are generated, a download bar appears to download the ZIP archive
 * - Validation status shown inline
 */

import React, { useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { AgentViewProps, ChatMessage } from 'framework/types';
import { ChatPanel, ActionButton } from 'framework/components';
import { useAgent } from 'framework/hooks';
import styles from './styles';

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

/**
 * CRC-32 lookup table (IEEE 802.3 polynomial).
 */
const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) {
      c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    }
    table[i] = c;
  }
  return table;
})();

const crc32 = (data: Uint8Array): number => {
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < data.length; i++) {
    crc = CRC_TABLE[(crc ^ data[i]) & 0xFF] ^ (crc >>> 8);
  }
  return (crc ^ 0xFFFFFFFF) >>> 0;
};

/**
 * Builds a valid ZIP file in-browser from a record of filepath->content entries.
 */
const buildZip = (files: Record<string, string>): Blob => {
  const encoder = new TextEncoder();
  const entries: { name: Uint8Array; data: Uint8Array; crc: number; offset: number }[] = [];
  const parts: Uint8Array[] = [];
  let offset = 0;

  for (const [filepath, content] of Object.entries(files)) {
    const nameBytes = encoder.encode(filepath);
    const dataBytes = encoder.encode(content);
    const crc = crc32(dataBytes);

    // Local file header (30 bytes)
    const header = new ArrayBuffer(30);
    const view = new DataView(header);
    view.setUint32(0, 0x04034b50, true);
    view.setUint16(4, 20, true);
    view.setUint16(6, 0, true);
    view.setUint16(8, 0, true);   // stored
    view.setUint16(10, 0, true);
    view.setUint16(12, 0, true);
    view.setUint32(14, crc, true);
    view.setUint32(18, dataBytes.length, true);
    view.setUint32(22, dataBytes.length, true);
    view.setUint16(26, nameBytes.length, true);
    view.setUint16(28, 0, true);

    const headerArr = new Uint8Array(header);
    parts.push(headerArr, nameBytes, dataBytes);
    entries.push({ name: nameBytes, data: dataBytes, crc, offset });
    offset += headerArr.length + nameBytes.length + dataBytes.length;
  }

  // Central directory
  const cdStart = offset;
  for (const entry of entries) {
    const cd = new ArrayBuffer(46);
    const cdv = new DataView(cd);
    cdv.setUint32(0, 0x02014b50, true);
    cdv.setUint16(4, 20, true);
    cdv.setUint16(6, 20, true);
    cdv.setUint16(8, 0, true);
    cdv.setUint16(10, 0, true);
    cdv.setUint16(12, 0, true);
    cdv.setUint16(14, 0, true);
    cdv.setUint32(16, entry.crc, true);
    cdv.setUint32(20, entry.data.length, true);
    cdv.setUint32(24, entry.data.length, true);
    cdv.setUint16(28, entry.name.length, true);
    cdv.setUint16(30, 0, true);
    cdv.setUint16(32, 0, true);
    cdv.setUint16(34, 0, true);
    cdv.setUint16(36, 0, true);
    cdv.setUint32(38, 0, true);
    cdv.setUint32(42, entry.offset, true);

    const cdArr = new Uint8Array(cd);
    parts.push(cdArr, entry.name);
    offset += cdArr.length + entry.name.length;
  }

  // End of central directory
  const eocd = new ArrayBuffer(22);
  const ev = new DataView(eocd);
  ev.setUint32(0, 0x06054b50, true);
  ev.setUint16(4, 0, true);
  ev.setUint16(6, 0, true);
  ev.setUint16(8, entries.length, true);
  ev.setUint16(10, entries.length, true);
  ev.setUint32(12, offset - cdStart, true);
  ev.setUint32(16, cdStart, true);
  ev.setUint16(20, 0, true);
  parts.push(new Uint8Array(eocd));

  return new Blob(parts, { type: 'application/zip' });
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

  // Extract generated files from conversation
  const generated = useMemo(() => extractFilesFromMessages(messages), [messages]);
  const hasFiles = generated !== null && Object.keys(generated.files).length > 0;

  const validation = generated?.validation || {};
  const isValid = validation.valid === true;
  const validationErrors = (validation.errors as string[]) || [];
  const validationWarnings = (validation.warnings as string[]) || [];

  /**
   * Download all generated files as a single ZIP archive.
   */
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

      {/* Download bar when files are generated */}
      {hasFiles && generated && (
        <div style={styles.downloadBar}>
          <div style={styles.downloadInfo}>
            <span style={styles.downloadLabel}>
              {Object.keys(generated.files).length} {t('agentCreator.filesGenerated')}
            </span>
            {isValid ? (
              <span style={styles.validationSuccess}>{t('agentCreator.validationPassed')}</span>
            ) : (
              <span style={styles.validationError}>
                {validationErrors.length} {t('agentCreator.errors')}
                {validationWarnings.length > 0 && `, ${validationWarnings.length} ${t('agentCreator.warnings')}`}
              </span>
            )}
          </div>
          <ActionButton
            label={t('agentCreator.downloadZip')}
            onClick={handleDownloadZip}
          />
        </div>
      )}

      {/* Chat — always full width */}
      <div style={styles.body}>
        <div style={styles.chatPanel}>
          <ChatPanel
            messages={messages}
            onSendMessage={sendMessage}
            isLoading={isLoading}
            streamingContent={streamingContent}
            placeholder={t('agentCreator.placeholder')}
          />
        </div>
      </div>
    </div>
  );
};

export default AgentCreatorView;
