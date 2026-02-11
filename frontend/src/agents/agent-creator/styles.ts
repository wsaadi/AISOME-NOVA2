/**
 * Styles for Agent Creator view.
 *
 * Full-width chat with a download bar when files are generated.
 */

const styles = {
  container: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    height: '100%',
    overflow: 'hidden' as const,
  },
  header: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    padding: '12px 16px',
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    minHeight: 48,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: 600,
    margin: 0,
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 8,
  },
  headerBadge: {
    display: 'inline-flex' as const,
    alignItems: 'center' as const,
    padding: '2px 8px',
    borderRadius: 12,
    fontSize: 11,
    fontWeight: 500,
    backgroundColor: 'var(--success-bg, #e8f5e9)',
    color: 'var(--success-color, #2e7d32)',
  },
  body: {
    display: 'flex' as const,
    flex: 1,
    overflow: 'hidden' as const,
  },
  chatPanel: {
    flex: 1,
    minWidth: 0,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    overflow: 'hidden' as const,
  },
  downloadBar: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    padding: '10px 16px',
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    backgroundColor: 'var(--surface-bg, #fafafa)',
  },
  downloadInfo: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 12,
  },
  downloadLabel: {
    fontSize: 13,
    fontWeight: 500,
  },
  validationSuccess: {
    color: 'var(--success-color, #2e7d32)',
    fontSize: 12,
    fontWeight: 500,
  },
  validationError: {
    color: 'var(--error-color, #d32f2f)',
    fontSize: 12,
    fontWeight: 500,
  },
  progressBar: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 8,
    padding: '4px 16px',
    fontSize: 12,
    color: 'var(--text-secondary, #666)',
  },
  progressFill: {
    height: 3,
    borderRadius: 2,
    backgroundColor: 'var(--primary-color, #1976d2)',
    transition: 'width 0.3s ease',
  },
  progressTrack: {
    flex: 1,
    height: 3,
    borderRadius: 2,
    backgroundColor: 'var(--divider-color, #e0e0e0)',
    overflow: 'hidden' as const,
  },
};

export default styles;
