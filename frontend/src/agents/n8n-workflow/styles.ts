/**
 * Styles for the N8N Workflow Agent execution view.
 *
 * Adapts to 4 UI modes: form, chat, pipeline, simple.
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
    padding: '14px 20px',
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    minHeight: 52,
  },
  headerLeft: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 12,
  },
  headerIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    color: '#fff',
    fontSize: 18,
    flexShrink: 0,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: 700,
    margin: 0,
  },
  headerDesc: {
    fontSize: 12,
    color: 'var(--text-secondary, #888)',
    margin: 0,
    maxWidth: 400,
    overflow: 'hidden' as const,
    textOverflow: 'ellipsis' as const,
    whiteSpace: 'nowrap' as const,
  },
  headerBadge: {
    padding: '3px 10px',
    borderRadius: 12,
    fontSize: 11,
    fontWeight: 600,
    backgroundColor: 'var(--primary-bg, #eef2ff)',
    color: 'var(--primary-color, #6366f1)',
  },

  // -- Content area --
  content: {
    flex: 1,
    overflow: 'auto' as const,
    display: 'flex' as const,
    flexDirection: 'column' as const,
  },

  // -- Form mode --
  formContainer: {
    flex: 1,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    padding: '24px 20px',
    gap: 16,
    maxWidth: 640,
    margin: '0 auto',
    width: '100%',
  },
  formTitle: {
    fontSize: 18,
    fontWeight: 700,
    marginBottom: 4,
  },
  formDesc: {
    fontSize: 13,
    color: 'var(--text-secondary, #888)',
    marginBottom: 16,
  },
  formField: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    gap: 4,
  },
  formLabel: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text-primary, #333)',
  },
  formRequired: {
    color: 'var(--error-color, #d32f2f)',
    marginLeft: 2,
  },
  formHint: {
    fontSize: 11,
    color: 'var(--text-secondary, #888)',
  },
  formInput: {
    padding: '10px 12px',
    borderRadius: 8,
    border: '1px solid var(--divider-color, #d0d0d0)',
    fontSize: 14,
    backgroundColor: 'var(--bg-color, #fff)',
    color: 'var(--text-primary, #333)',
    outline: 'none',
    transition: 'border-color 0.2s',
  },
  formTextarea: {
    padding: '10px 12px',
    borderRadius: 8,
    border: '1px solid var(--divider-color, #d0d0d0)',
    fontSize: 14,
    backgroundColor: 'var(--bg-color, #fff)',
    color: 'var(--text-primary, #333)',
    minHeight: 100,
    resize: 'vertical' as const,
    fontFamily: 'inherit',
    outline: 'none',
  },
  formSelect: {
    padding: '10px 12px',
    borderRadius: 8,
    border: '1px solid var(--divider-color, #d0d0d0)',
    fontSize: 14,
    backgroundColor: 'var(--bg-color, #fff)',
    color: 'var(--text-primary, #333)',
    outline: 'none',
  },
  formFileInput: {
    padding: '10px 12px',
    borderRadius: 8,
    border: '1px dashed var(--divider-color, #d0d0d0)',
    fontSize: 13,
    backgroundColor: 'var(--surface-bg, #fafafa)',
    cursor: 'pointer' as const,
  },
  formSubmitRow: {
    display: 'flex' as const,
    justifyContent: 'flex-end' as const,
    paddingTop: 8,
  },

  // -- Pipeline mode --
  pipelineContainer: {
    flex: 1,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    padding: '24px 20px',
    gap: 0,
  },
  pipelineStep: {
    display: 'flex' as const,
    alignItems: 'flex-start' as const,
    gap: 16,
    padding: '16px 0',
    position: 'relative' as const,
  },
  pipelineStepLine: {
    position: 'absolute' as const,
    left: 17,
    top: 44,
    bottom: 0,
    width: 2,
    backgroundColor: 'var(--divider-color, #e0e0e0)',
  },
  pipelineStepDot: {
    width: 36,
    height: 36,
    borderRadius: '50%',
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    fontSize: 14,
    fontWeight: 700,
    flexShrink: 0,
    zIndex: 1,
  },
  pipelineStepDotPending: {
    backgroundColor: 'var(--surface-bg, #f0f0f0)',
    color: 'var(--text-secondary, #888)',
    border: '2px solid var(--divider-color, #d0d0d0)',
  },
  pipelineStepDotActive: {
    backgroundColor: 'var(--primary-color, #6366f1)',
    color: '#fff',
    border: '2px solid var(--primary-color, #6366f1)',
  },
  pipelineStepDotDone: {
    backgroundColor: '#059669',
    color: '#fff',
    border: '2px solid #059669',
  },
  pipelineStepContent: {
    flex: 1,
  },
  pipelineStepName: {
    fontSize: 14,
    fontWeight: 600,
    marginBottom: 2,
  },
  pipelineStepDesc: {
    fontSize: 12,
    color: 'var(--text-secondary, #888)',
  },
  pipelineStepHuman: {
    marginTop: 8,
    padding: '8px 12px',
    borderRadius: 8,
    border: '1px solid #fbbf24',
    backgroundColor: '#fffbeb',
    fontSize: 12,
    color: '#92400e',
  },

  // -- Simple mode --
  simpleContainer: {
    flex: 1,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    padding: 32,
    gap: 16,
  },
  simpleIcon: {
    fontSize: 64,
    color: 'var(--primary-color, #6366f1)',
    opacity: 0.5,
  },
  simpleTitle: {
    fontSize: 18,
    fontWeight: 700,
    textAlign: 'center' as const,
  },
  simpleDesc: {
    fontSize: 14,
    color: 'var(--text-secondary, #888)',
    textAlign: 'center' as const,
    maxWidth: 400,
  },

  // -- Chat mode (uses ChatPanel) --
  chatContainer: {
    flex: 1,
    minHeight: 0,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    overflow: 'hidden' as const,
  },

  // -- Execution result --
  resultContainer: {
    padding: '20px',
    borderTop: '1px solid var(--divider-color, #e0e0e0)',
  },
  resultHeader: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 8,
    marginBottom: 12,
  },
  resultIcon: {
    fontSize: 20,
    color: '#059669',
  },
  resultTitle: {
    fontSize: 15,
    fontWeight: 700,
  },
  resultContent: {
    padding: '12px 16px',
    borderRadius: 10,
    border: '1px solid var(--divider-color, #e0e0e0)',
    backgroundColor: 'var(--bg-color, #fff)',
    fontSize: 13,
    whiteSpace: 'pre-wrap' as const,
    fontFamily: 'monospace',
    maxHeight: 400,
    overflow: 'auto' as const,
  },
  resultError: {
    padding: '12px 16px',
    borderRadius: 10,
    border: '1px solid var(--error-color, #d32f2f)',
    backgroundColor: '#fef2f2',
    color: 'var(--error-color, #d32f2f)',
    fontSize: 13,
  },

  // -- Loading / Executing state --
  executingOverlay: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    gap: 12,
    padding: 32,
  },
  executingText: {
    fontSize: 14,
    fontWeight: 500,
    color: 'var(--text-secondary, #888)',
  },
  spinner: {
    width: 32,
    height: 32,
    border: '3px solid var(--divider-color, #e0e0e0)',
    borderTopColor: 'var(--primary-color, #6366f1)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
};

export default styles;
