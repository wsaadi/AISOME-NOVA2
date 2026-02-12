/**
 * Styles for the Agent Creator view.
 *
 * Layout: vertical flex — header, progress, results panel (when files), chat.
 */

const styles = {
  // -- Layout --
  container: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    height: '100%',
    overflow: 'hidden' as const,
  },

  // -- Header --
  header: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    padding: '10px 16px',
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    minHeight: 44,
  },
  headerLeft: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 8,
  },
  headerIcon: {
    fontSize: 18,
  },
  headerTitle: {
    fontSize: 15,
    fontWeight: 600,
    margin: 0,
  },
  slugBadge: {
    display: 'inline-flex' as const,
    alignItems: 'center' as const,
    padding: '2px 8px',
    borderRadius: 12,
    fontSize: 11,
    fontWeight: 500,
    backgroundColor: 'var(--success-bg, #e8f5e9)',
    color: 'var(--success-color, #2e7d32)',
  },

  // -- Progress --
  progressBar: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 8,
    padding: '4px 16px',
    fontSize: 12,
    color: 'var(--text-secondary, #666)',
  },
  progressTrack: {
    flex: 1,
    height: 3,
    borderRadius: 2,
    backgroundColor: 'var(--divider-color, #e0e0e0)',
    overflow: 'hidden' as const,
  },
  progressFill: {
    height: 3,
    borderRadius: 2,
    backgroundColor: 'var(--primary-color, #1976d2)',
    transition: 'width 0.3s ease',
  },
  progressText: {
    fontSize: 11,
    whiteSpace: 'nowrap' as const,
  },

  // -- Error --
  errorBanner: {
    padding: '8px 16px',
    color: 'var(--error-color, #d32f2f)',
    fontSize: 13,
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
  },

  // -- Results panel --
  resultsPanel: {
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    backgroundColor: 'var(--surface-bg, #fafafa)',
    maxHeight: '45%',
    overflow: 'auto' as const,
  },

  // Validation
  validationRow: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 12,
    padding: '10px 16px 6px',
    fontSize: 13,
  },
  validationPass: {
    color: 'var(--success-color, #2e7d32)',
    fontWeight: 600,
    fontSize: 13,
  },
  validationFail: {
    color: 'var(--error-color, #d32f2f)',
    fontWeight: 600,
    fontSize: 13,
  },
  validationWarn: {
    color: 'var(--warning-color, #ed6c02)',
    fontSize: 12,
  },
  spacer: {
    flex: 1,
  },
  fileCount: {
    fontSize: 12,
    color: 'var(--text-secondary, #888)',
  },
  validationDetail: {
    padding: '4px 16px 8px',
  },
  validationErrorItem: {
    fontSize: 12,
    color: 'var(--error-color, #d32f2f)',
    padding: '2px 0',
  },

  // File list
  fileListHeader: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    padding: '6px 16px',
    borderTop: '1px solid var(--divider-color, #e0e0e0)',
  },
  fileListTitle: {
    fontSize: 12,
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    color: 'var(--text-secondary, #888)',
    letterSpacing: 0.5,
  },
  fileListActions: {
    display: 'flex' as const,
    gap: 12,
  },
  linkBtn: {
    fontSize: 12,
    color: 'var(--primary-color, #1976d2)',
    cursor: 'pointer' as const,
    userSelect: 'none' as const,
  },
  fileList: {
    padding: '0 16px 8px',
  },
  fileItem: {
    borderRadius: 6,
    border: '1px solid var(--divider-color, #e0e0e0)',
    marginBottom: 4,
    overflow: 'hidden' as const,
    backgroundColor: 'var(--bg-color, #fff)',
  },
  fileItemHeader: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 6,
    padding: '6px 10px',
    cursor: 'pointer' as const,
    userSelect: 'none' as const,
    fontSize: 13,
  },
  fileToggle: {
    fontSize: 10,
    color: 'var(--text-secondary, #888)',
    width: 14,
    textAlign: 'center' as const,
  },
  fileName: {
    fontFamily: 'monospace',
    fontSize: 12,
    fontWeight: 500,
  },
  filePreview: {
    borderTop: '1px solid var(--divider-color, #e0e0e0)',
    padding: '0 8px',
    maxHeight: 300,
    overflow: 'auto' as const,
    fontSize: 12,
  },

  // Download
  downloadRow: {
    display: 'flex' as const,
    justifyContent: 'flex-end' as const,
    padding: '8px 16px',
    borderTop: '1px solid var(--divider-color, #e0e0e0)',
  },

  // -- Chat --
  chatArea: {
    flex: 1,
    minHeight: 0,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    overflow: 'hidden' as const,
  },
};

export default styles;
