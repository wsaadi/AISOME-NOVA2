/**
 * Styles for the Workflow Studio view.
 *
 * Layout: vertical flex — header, tabs, content area (chat + results).
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
    padding: '12px 16px',
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    minHeight: 48,
  },
  headerLeft: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 10,
  },
  headerIcon: {
    fontSize: 20,
    opacity: 0.8,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: 700,
    margin: 0,
  },
  headerSubtitle: {
    fontSize: 12,
    color: 'var(--text-secondary, #888)',
    margin: 0,
  },
  headerRight: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 8,
  },

  // -- Tabs --
  tabBar: {
    display: 'flex' as const,
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    padding: '0 16px',
    gap: 0,
  },
  tab: {
    padding: '10px 16px',
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--text-secondary, #888)',
    cursor: 'pointer' as const,
    borderBottom: '2px solid transparent',
    userSelect: 'none' as const,
    transition: 'color 0.2s, border-color 0.2s',
  },
  tabActive: {
    padding: '10px 16px',
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--primary-color, #6366f1)',
    cursor: 'pointer' as const,
    borderBottom: '2px solid var(--primary-color, #6366f1)',
    userSelect: 'none' as const,
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
    backgroundColor: 'var(--primary-color, #6366f1)',
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

  // -- Chat area --
  chatArea: {
    flex: 1,
    minHeight: 0,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    overflow: 'hidden' as const,
  },

  // -- Import area --
  importArea: {
    flex: 1,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    padding: 32,
    gap: 20,
  },
  importDropzone: {
    width: '100%',
    maxWidth: 500,
    padding: '40px 32px',
    border: '2px dashed var(--divider-color, #ccc)',
    borderRadius: 16,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    alignItems: 'center' as const,
    gap: 12,
    cursor: 'pointer' as const,
    transition: 'border-color 0.2s, background-color 0.2s',
    backgroundColor: 'var(--surface-bg, #fafafa)',
  },
  importIcon: {
    fontSize: 48,
    color: 'var(--primary-color, #6366f1)',
    opacity: 0.6,
  },
  importTitle: {
    fontSize: 16,
    fontWeight: 600,
    margin: 0,
  },
  importDesc: {
    fontSize: 13,
    color: 'var(--text-secondary, #888)',
    textAlign: 'center' as const,
    margin: 0,
    maxWidth: 350,
  },
  importOr: {
    fontSize: 13,
    color: 'var(--text-secondary, #888)',
    margin: '8px 0',
  },
  importPasteArea: {
    width: '100%',
    maxWidth: 500,
  },
  importTextarea: {
    width: '100%',
    minHeight: 150,
    padding: 12,
    borderRadius: 8,
    border: '1px solid var(--divider-color, #e0e0e0)',
    fontFamily: 'monospace',
    fontSize: 12,
    resize: 'vertical' as const,
    backgroundColor: 'var(--bg-color, #fff)',
    color: 'var(--text-primary, #333)',
  },

  // -- Results panel (workflow generated) --
  resultsPanel: {
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    backgroundColor: 'var(--surface-bg, #fafafa)',
    maxHeight: '50%',
    overflow: 'auto' as const,
  },
  resultHeader: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    padding: '12px 16px',
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
  },
  resultTitle: {
    fontSize: 14,
    fontWeight: 600,
    margin: 0,
  },
  resultBadge: {
    display: 'inline-flex' as const,
    alignItems: 'center' as const,
    padding: '3px 10px',
    borderRadius: 12,
    fontSize: 11,
    fontWeight: 600,
    backgroundColor: 'var(--success-bg, #e8f5e9)',
    color: 'var(--success-color, #2e7d32)',
  },

  // -- Analysis cards --
  analysisGrid: {
    display: 'grid' as const,
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: 12,
    padding: '12px 16px',
  },
  analysisCard: {
    padding: '10px 14px',
    borderRadius: 10,
    border: '1px solid var(--divider-color, #e0e0e0)',
    backgroundColor: 'var(--bg-color, #fff)',
  },
  analysisLabel: {
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    color: 'var(--text-secondary, #888)',
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  analysisValue: {
    fontSize: 14,
    fontWeight: 600,
    color: 'var(--text-primary, #333)',
  },

  // -- Steps list --
  stepsSection: {
    padding: '0 16px 12px',
  },
  stepsTitle: {
    fontSize: 12,
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    color: 'var(--text-secondary, #888)',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  stepsList: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    gap: 4,
  },
  stepItem: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 10,
    padding: '6px 10px',
    borderRadius: 8,
    border: '1px solid var(--divider-color, #e0e0e0)',
    backgroundColor: 'var(--bg-color, #fff)',
    fontSize: 13,
  },
  stepOrder: {
    width: 22,
    height: 22,
    borderRadius: '50%',
    backgroundColor: 'var(--primary-color, #6366f1)',
    color: '#fff',
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    fontSize: 11,
    fontWeight: 700,
    flexShrink: 0,
  },
  stepName: {
    fontWeight: 500,
    flex: 1,
  },
  stepCategory: {
    fontSize: 11,
    padding: '1px 6px',
    borderRadius: 4,
    backgroundColor: 'var(--surface-bg, #f0f0f0)',
    color: 'var(--text-secondary, #888)',
  },
  stepHumanBadge: {
    fontSize: 10,
    padding: '1px 6px',
    borderRadius: 4,
    backgroundColor: '#fff3e0',
    color: '#e65100',
    fontWeight: 600,
  },

  // -- Inputs list --
  inputsSection: {
    padding: '0 16px 12px',
  },
  inputItem: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 8,
    padding: '4px 0',
    fontSize: 13,
  },
  inputType: {
    fontSize: 11,
    padding: '1px 6px',
    borderRadius: 4,
    backgroundColor: 'var(--primary-bg, #e8eaf6)',
    color: 'var(--primary-color, #6366f1)',
    fontWeight: 500,
    fontFamily: 'monospace',
  },
  inputRequired: {
    fontSize: 10,
    color: 'var(--error-color, #d32f2f)',
    fontWeight: 600,
  },

  // -- Publish row --
  publishRow: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'flex-end' as const,
    gap: 8,
    padding: '10px 16px',
    borderTop: '1px solid var(--divider-color, #e0e0e0)',
  },
  publishMessage: {
    padding: '6px 16px',
    fontSize: 13,
    fontWeight: 500,
  },

  // -- N8N Editor iframe --
  editorArea: {
    flex: 1,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    overflow: 'hidden' as const,
  },
  iframe: {
    flex: 1,
    border: 'none',
    width: '100%',
  },
};

export default styles;
