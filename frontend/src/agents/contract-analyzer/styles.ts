/**
 * Styles for the Contract Analyzer view.
 *
 * Layout: header (tabs + settings) → content area (analysis | chat | themes).
 */

const styles = {
  // -- Layout --
  container: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    height: '100%',
    overflow: 'hidden' as const,
  },

  // -- Header with tabs --
  header: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    padding: '0 16px',
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    minHeight: 48,
    flexShrink: 0,
  },
  tabs: {
    display: 'flex' as const,
    gap: 0,
  },
  tab: {
    padding: '12px 20px',
    border: 'none' as const,
    background: 'none' as const,
    cursor: 'pointer' as const,
    fontSize: 14,
    fontWeight: 500,
    color: 'var(--text-secondary, #666)',
    borderBottom: '2px solid transparent',
    transition: 'all 0.2s ease',
  },
  tabActive: {
    color: 'var(--primary-color, #1976d2)',
    borderBottomColor: 'var(--primary-color, #1976d2)',
    fontWeight: 600,
  },
  settingsArea: {
    flexShrink: 0,
  },

  // -- Content --
  content: {
    flex: 1,
    minHeight: 0,
    overflow: 'auto' as const,
    display: 'flex' as const,
    flexDirection: 'column' as const,
  },

  // -- Upload --
  uploadContainer: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    padding: 40,
    flex: 1,
    gap: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 600,
    margin: '0 0 12px',
    color: 'var(--text-primary, #333)',
  },

  // -- Progress --
  progressContainer: {
    width: '100%',
    maxWidth: 400,
    marginTop: 16,
  },
  progressBar: {
    height: 4,
    borderRadius: 2,
    backgroundColor: 'var(--divider-color, #e0e0e0)',
    overflow: 'hidden' as const,
  },
  progressFill: {
    height: '100%',
    borderRadius: 2,
    backgroundColor: 'var(--primary-color, #1976d2)',
    transition: 'width 0.3s ease',
  },
  progressText: {
    fontSize: 12,
    color: 'var(--text-secondary, #666)',
    textAlign: 'center' as const,
    marginTop: 6,
  },

  // -- Analysis tab --
  analysisContainer: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    flex: 1,
    overflow: 'auto' as const,
  },
  analysisHeader: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    padding: '12px 16px',
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    flexShrink: 0,
  },
  analysisTitle: {
    fontSize: 15,
    fontWeight: 600,
    margin: 0,
    color: 'var(--text-primary, #333)',
  },
  analysisActions: {
    display: 'flex' as const,
    gap: 8,
  },
  analysisContent: {
    padding: 16,
    overflow: 'auto' as const,
    flex: 1,
  },

  // -- Risk table --
  riskTableContainer: {
    padding: '0 16px 16px',
    flexShrink: 0,
  },

  // -- Recommendations tab --
  recommendationsContainer: {
    padding: 24,
    flex: 1,
    overflow: 'auto' as const,
  },
  helpText: {
    fontSize: 13,
    color: 'var(--text-secondary, #888)',
    margin: '0 0 16px',
  },
  themeGrid: {
    display: 'grid' as const,
    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
    gap: 12,
    marginTop: 8,
  },
  themeCard: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 10,
    padding: '14px 16px',
    borderRadius: 8,
    border: '1px solid var(--divider-color, #e0e0e0)',
    backgroundColor: 'var(--bg-color, #fff)',
    cursor: 'pointer' as const,
    transition: 'all 0.15s ease',
  },
  themeCardActive: {
    borderColor: 'var(--primary-color, #1976d2)',
    backgroundColor: 'var(--primary-bg, #e3f2fd)',
  },
  themeIcon: {
    fontSize: 20,
    flexShrink: 0,
  },
  themeLabel: {
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--text-primary, #333)',
  },
  noAnalysisMessage: {
    textAlign: 'center' as const,
    padding: '32px 0',
    color: 'var(--text-secondary, #888)',
    fontSize: 14,
  },

  // -- Chat tab --
  chatContainer: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    flex: 1,
    minHeight: 0,
    overflow: 'hidden' as const,
  },
  chatHeader: {
    padding: '12px 16px',
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    flexShrink: 0,
  },

  // -- Utility --
  spacer: {
    flex: 1,
  },
};

export default styles;
