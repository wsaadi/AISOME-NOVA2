/**
 * Styles for the Tender Assistant view.
 *
 * Professional, ergonomic layout with:
 *   - Left navigation sidebar
 *   - Main content area
 *   - Optional right chat panel
 */

const SIDEBAR_WIDTH = 240;
const CHAT_WIDTH = 380;

const styles = {
  // ==========================================================================
  // Root layout
  // ==========================================================================
  root: {
    display: 'flex' as const,
    height: '100%',
    overflow: 'hidden' as const,
    fontFamily: '"Inter", "Roboto", "Helvetica Neue", sans-serif',
  },

  // ==========================================================================
  // Left sidebar
  // ==========================================================================
  sidebar: {
    width: SIDEBAR_WIDTH,
    minWidth: SIDEBAR_WIDTH,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    borderRight: '1px solid var(--divider-color, #e0e0e0)',
    backgroundColor: 'var(--sidebar-bg, #fafafa)',
    overflow: 'hidden' as const,
  },
  sidebarHeader: {
    padding: '16px 16px 12px',
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
  },
  sidebarTitle: {
    fontSize: 15,
    fontWeight: 700,
    color: 'var(--text-primary, #1a1a1a)',
    margin: 0,
    letterSpacing: '-0.2px',
  },
  sidebarSubtitle: {
    fontSize: 11,
    color: 'var(--text-secondary, #888)',
    margin: '4px 0 0',
  },
  navList: {
    flex: 1,
    overflow: 'auto' as const,
    padding: '8px 0',
  },
  navItem: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 10,
    padding: '10px 16px',
    cursor: 'pointer' as const,
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--text-secondary, #555)',
    transition: 'all 0.15s ease',
    border: 'none' as const,
    background: 'none' as const,
    width: '100%',
    textAlign: 'left' as const,
    borderLeft: '3px solid transparent',
  },
  navItemActive: {
    color: 'var(--primary-color, #1976d2)',
    backgroundColor: 'var(--primary-bg, rgba(25, 118, 210, 0.06))',
    borderLeftColor: 'var(--primary-color, #1976d2)',
    fontWeight: 600,
  },
  navIcon: {
    fontSize: 20,
    width: 20,
    textAlign: 'center' as const,
    flexShrink: 0,
    opacity: 0.8,
  },
  navLabel: {
    flex: 1,
    whiteSpace: 'nowrap' as const,
    overflow: 'hidden' as const,
    textOverflow: 'ellipsis' as const,
  },
  navBadge: {
    fontSize: 10,
    fontWeight: 700,
    padding: '2px 6px',
    borderRadius: 10,
    backgroundColor: 'var(--primary-color, #1976d2)',
    color: '#fff',
    minWidth: 18,
    textAlign: 'center' as const,
  },
  sidebarFooter: {
    padding: '12px 16px',
    borderTop: '1px solid var(--divider-color, #e0e0e0)',
    fontSize: 11,
    color: 'var(--text-secondary, #999)',
  },

  // ==========================================================================
  // Main content
  // ==========================================================================
  main: {
    flex: 1,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    minWidth: 0,
    overflow: 'hidden' as const,
  },
  mainHeader: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    padding: '12px 20px',
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    minHeight: 52,
    flexShrink: 0,
  },
  mainTitle: {
    fontSize: 16,
    fontWeight: 700,
    color: 'var(--text-primary, #1a1a1a)',
    margin: 0,
  },
  mainActions: {
    display: 'flex' as const,
    gap: 8,
    alignItems: 'center' as const,
  },
  mainContent: {
    flex: 1,
    overflow: 'auto' as const,
    padding: 20,
  },

  // ==========================================================================
  // Right chat panel
  // ==========================================================================
  chatPanel: {
    width: CHAT_WIDTH,
    minWidth: CHAT_WIDTH,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    borderLeft: '1px solid var(--divider-color, #e0e0e0)',
    backgroundColor: 'var(--bg-color, #fff)',
  },
  chatPanelCollapsed: {
    width: 0,
    minWidth: 0,
    overflow: 'hidden' as const,
  },
  chatToggle: {
    padding: '4px 8px',
    fontSize: 12,
    border: '1px solid var(--divider-color, #ddd)',
    borderRadius: 4,
    background: 'var(--bg-color, #fff)',
    cursor: 'pointer' as const,
    color: 'var(--text-secondary, #666)',
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 4,
  },
  chatHeader: {
    padding: '12px 16px',
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
  },
  chatTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text-primary, #333)',
    margin: 0,
  },

  // ==========================================================================
  // Document library
  // ==========================================================================
  docGrid: {
    display: 'grid' as const,
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: 12,
    marginTop: 16,
  },
  docCard: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    padding: 14,
    borderRadius: 8,
    border: '1px solid var(--divider-color, #e0e0e0)',
    backgroundColor: 'var(--bg-color, #fff)',
    transition: 'box-shadow 0.15s ease',
    cursor: 'default' as const,
  },
  docCardHeader: {
    display: 'flex' as const,
    alignItems: 'flex-start' as const,
    justifyContent: 'space-between' as const,
    gap: 8,
  },
  docFileName: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text-primary, #333)',
    margin: 0,
    wordBreak: 'break-word' as const,
    flex: 1,
  },
  docCategory: {
    fontSize: 10,
    fontWeight: 600,
    padding: '3px 8px',
    borderRadius: 4,
    textTransform: 'uppercase' as const,
    whiteSpace: 'nowrap' as const,
    letterSpacing: '0.3px',
  },
  docMeta: {
    fontSize: 11,
    color: 'var(--text-secondary, #888)',
    marginTop: 6,
  },
  docTags: {
    display: 'flex' as const,
    flexWrap: 'wrap' as const,
    gap: 4,
    marginTop: 8,
  },
  docTag: {
    fontSize: 10,
    padding: '2px 6px',
    borderRadius: 3,
    backgroundColor: 'var(--divider-color, #f0f0f0)',
    color: 'var(--text-secondary, #666)',
  },
  docActions: {
    display: 'flex' as const,
    gap: 4,
    marginTop: 10,
    paddingTop: 8,
    borderTop: '1px solid var(--divider-color, #f0f0f0)',
  },
  uploadArea: {
    marginBottom: 16,
  },
  filterBar: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 8,
    flexWrap: 'wrap' as const,
  },
  filterChip: {
    fontSize: 11,
    padding: '4px 10px',
    borderRadius: 12,
    border: '1px solid var(--divider-color, #ddd)',
    backgroundColor: 'var(--bg-color, #fff)',
    cursor: 'pointer' as const,
    transition: 'all 0.15s ease',
    fontWeight: 500,
    color: 'var(--text-secondary, #666)',
  },
  filterChipActive: {
    backgroundColor: 'var(--primary-color, #1976d2)',
    borderColor: 'var(--primary-color, #1976d2)',
    color: '#fff',
  },

  // ==========================================================================
  // Analysis view
  // ==========================================================================
  analysisLayout: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    gap: 16,
  },
  analysisCard: {
    padding: 16,
    borderRadius: 8,
    border: '1px solid var(--divider-color, #e0e0e0)',
    backgroundColor: 'var(--bg-color, #fff)',
  },
  analysisCardHeader: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    marginBottom: 12,
  },
  analysisCardTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: 'var(--text-primary, #333)',
    margin: 0,
  },
  comparisonBanner: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 12,
    padding: 16,
    borderRadius: 8,
    backgroundColor: 'var(--primary-bg, #e3f2fd)',
    border: '1px solid var(--primary-color, #90caf9)',
    marginBottom: 16,
  },
  statGrid: {
    display: 'grid' as const,
    gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
    gap: 12,
    marginBottom: 16,
  },
  statCard: {
    textAlign: 'center' as const,
    padding: 12,
    borderRadius: 8,
    backgroundColor: 'var(--bg-color, #fafafa)',
    border: '1px solid var(--divider-color, #e0e0e0)',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 700,
    margin: 0,
  },
  statLabel: {
    fontSize: 11,
    color: 'var(--text-secondary, #888)',
    marginTop: 4,
  },

  // ==========================================================================
  // Response editor
  // ==========================================================================
  editorLayout: {
    display: 'flex' as const,
    height: '100%',
    overflow: 'hidden' as const,
  },
  chapterTree: {
    width: 280,
    minWidth: 280,
    borderRight: '1px solid var(--divider-color, #e0e0e0)',
    overflow: 'auto' as const,
    padding: '8px 0',
    flexShrink: 0,
  },
  chapterItem: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 8,
    padding: '8px 12px',
    cursor: 'pointer' as const,
    fontSize: 12,
    color: 'var(--text-primary, #333)',
    transition: 'background-color 0.1s ease',
    border: 'none' as const,
    background: 'none' as const,
    width: '100%',
    textAlign: 'left' as const,
  },
  chapterItemActive: {
    backgroundColor: 'var(--primary-bg, rgba(25, 118, 210, 0.08))',
    fontWeight: 600,
  },
  chapterNumber: {
    fontSize: 11,
    fontWeight: 700,
    color: 'var(--primary-color, #1976d2)',
    minWidth: 28,
  },
  chapterTitle: {
    flex: 1,
    overflow: 'hidden' as const,
    textOverflow: 'ellipsis' as const,
    whiteSpace: 'nowrap' as const,
  },
  chapterStatus: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    flexShrink: 0,
  },
  subChapter: {
    paddingLeft: 28,
  },
  editorArea: {
    flex: 1,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    minWidth: 0,
    overflow: 'hidden' as const,
  },
  editorHeader: {
    padding: '12px 16px',
    borderBottom: '1px solid var(--divider-color, #e0e0e0)',
    flexShrink: 0,
  },
  editorChapterTitle: {
    fontSize: 15,
    fontWeight: 600,
    color: 'var(--text-primary, #333)',
    margin: 0,
  },
  editorChapterDesc: {
    fontSize: 12,
    color: 'var(--text-secondary, #888)',
    marginTop: 4,
  },
  editorToolbar: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 6,
    padding: '8px 16px',
    borderBottom: '1px solid var(--divider-color, #f0f0f0)',
    flexShrink: 0,
    flexWrap: 'wrap' as const,
  },
  editorContent: {
    flex: 1,
    overflow: 'auto' as const,
    padding: 16,
  },
  textarea: {
    width: '100%',
    minHeight: 300,
    padding: 12,
    fontSize: 13,
    lineHeight: 1.7,
    border: '1px solid var(--divider-color, #e0e0e0)',
    borderRadius: 6,
    resize: 'vertical' as const,
    fontFamily: '"Inter", sans-serif',
    color: 'var(--text-primary, #333)',
    backgroundColor: 'var(--bg-color, #fff)',
    outline: 'none' as const,
  },
  editorPlaceholder: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    flex: 1,
    color: 'var(--text-secondary, #999)',
    fontSize: 14,
    gap: 8,
  },
  keyPointsList: {
    margin: '8px 0 0',
    padding: '0 0 0 16px',
    fontSize: 12,
    color: 'var(--text-secondary, #666)',
    lineHeight: 1.6,
  },

  // ==========================================================================
  // Compliance checker
  // ==========================================================================
  complianceScore: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    gap: 20,
    padding: 24,
    marginBottom: 16,
  },
  scoreCircle: {
    width: 100,
    height: 100,
    borderRadius: '50%',
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    flexDirection: 'column' as const,
    border: '4px solid',
  },
  scoreValue: {
    fontSize: 28,
    fontWeight: 700,
  },
  scoreLabel: {
    fontSize: 10,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  issuesList: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    gap: 8,
  },
  issueItem: {
    display: 'flex' as const,
    alignItems: 'flex-start' as const,
    gap: 10,
    padding: 12,
    borderRadius: 6,
    border: '1px solid var(--divider-color, #e0e0e0)',
    fontSize: 12,
  },
  issueSeverity: {
    fontSize: 10,
    fontWeight: 700,
    padding: '2px 6px',
    borderRadius: 3,
    textTransform: 'uppercase' as const,
    whiteSpace: 'nowrap' as const,
  },

  // ==========================================================================
  // Export panel
  // ==========================================================================
  exportContainer: {
    maxWidth: 600,
    margin: '0 auto',
  },
  exportSection: {
    marginBottom: 24,
    padding: 16,
    borderRadius: 8,
    border: '1px solid var(--divider-color, #e0e0e0)',
  },
  exportLabel: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text-primary, #333)',
    marginBottom: 8,
    display: 'block' as const,
  },
  exportInput: {
    width: '100%',
    padding: '8px 12px',
    fontSize: 13,
    border: '1px solid var(--divider-color, #ddd)',
    borderRadius: 4,
    color: 'var(--text-primary, #333)',
    backgroundColor: 'var(--bg-color, #fff)',
    outline: 'none' as const,
  },

  // ==========================================================================
  // Improvements panel
  // ==========================================================================
  improvementCard: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    padding: 14,
    borderRadius: 8,
    border: '1px solid var(--divider-color, #e0e0e0)',
    backgroundColor: 'var(--bg-color, #fff)',
    marginBottom: 8,
  },
  improvementHeader: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    gap: 8,
  },
  improvementTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text-primary, #333)',
    margin: 0,
    flex: 1,
  },
  priorityBadge: {
    fontSize: 10,
    fontWeight: 700,
    padding: '2px 8px',
    borderRadius: 4,
    textTransform: 'uppercase' as const,
  },
  improvementDesc: {
    fontSize: 12,
    color: 'var(--text-secondary, #666)',
    marginTop: 6,
    lineHeight: 1.5,
  },
  addForm: {
    padding: 16,
    borderRadius: 8,
    border: '2px dashed var(--divider-color, #ddd)',
    marginBottom: 16,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    gap: 10,
  },
  formRow: {
    display: 'flex' as const,
    gap: 8,
    alignItems: 'center' as const,
  },
  inputField: {
    flex: 1,
    padding: '8px 10px',
    fontSize: 13,
    border: '1px solid var(--divider-color, #ddd)',
    borderRadius: 4,
    outline: 'none' as const,
    color: 'var(--text-primary, #333)',
    backgroundColor: 'var(--bg-color, #fff)',
  },
  selectField: {
    padding: '8px 10px',
    fontSize: 13,
    border: '1px solid var(--divider-color, #ddd)',
    borderRadius: 4,
    outline: 'none' as const,
    color: 'var(--text-primary, #333)',
    backgroundColor: 'var(--bg-color, #fff)',
  },

  // ==========================================================================
  // Buttons
  // ==========================================================================
  btn: {
    padding: '6px 14px',
    fontSize: 12,
    fontWeight: 600,
    borderRadius: 4,
    border: 'none' as const,
    cursor: 'pointer' as const,
    transition: 'opacity 0.15s ease',
    display: 'inline-flex' as const,
    alignItems: 'center' as const,
    gap: 6,
  },
  btnPrimary: {
    backgroundColor: 'var(--primary-color, #1976d2)',
    color: '#fff',
  },
  btnSecondary: {
    backgroundColor: 'var(--divider-color, #e0e0e0)',
    color: 'var(--text-primary, #333)',
  },
  btnDanger: {
    backgroundColor: '#d32f2f',
    color: '#fff',
  },
  btnSmall: {
    padding: '4px 8px',
    fontSize: 11,
  },
  btnDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed' as const,
  },

  // ==========================================================================
  // Common
  // ==========================================================================
  sectionTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: 'var(--text-primary, #333)',
    margin: '0 0 8px',
  },
  helpText: {
    fontSize: 12,
    color: 'var(--text-secondary, #888)',
    margin: '0 0 12px',
    lineHeight: 1.5,
  },
  emptyState: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    padding: 40,
    color: 'var(--text-secondary, #999)',
    textAlign: 'center' as const,
    gap: 8,
  },
  emptyIcon: {
    fontSize: 40,
    opacity: 0.4,
  },
  emptyText: {
    fontSize: 13,
  },
  divider: {
    height: 1,
    backgroundColor: 'var(--divider-color, #e0e0e0)',
    margin: '16px 0',
  },
  progressBar: {
    height: 4,
    borderRadius: 2,
    backgroundColor: 'var(--divider-color, #e0e0e0)',
    overflow: 'hidden' as const,
    margin: '8px 0',
  },
  progressFill: {
    height: '100%',
    borderRadius: 2,
    backgroundColor: 'var(--primary-color, #1976d2)',
    transition: 'width 0.3s ease',
  },
  progressText: {
    fontSize: 11,
    color: 'var(--text-secondary, #888)',
    textAlign: 'center' as const,
  },
  markdownContent: {
    fontSize: 13,
    lineHeight: 1.7,
    color: 'var(--text-primary, #333)',
  },
};

export default styles;

// Category colors
export const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  ancien_ao: { bg: '#fff3e0', text: '#e65100' },
  nouvel_ao: { bg: '#e3f2fd', text: '#1565c0' },
  ancienne_reponse: { bg: '#f3e5f5', text: '#7b1fa2' },
  template: { bg: '#e8f5e9', text: '#2e7d32' },
  other: { bg: '#f5f5f5', text: '#616161' },
};

// Priority colors
export const PRIORITY_COLORS: Record<string, { bg: string; text: string }> = {
  critique: { bg: '#ffebee', text: '#c62828' },
  haute: { bg: '#fff3e0', text: '#e65100' },
  normal: { bg: '#e3f2fd', text: '#1565c0' },
  basse: { bg: '#f5f5f5', text: '#616161' },
};

// Chapter status colors
export const STATUS_COLORS: Record<string, string> = {
  draft: '#bdbdbd',
  writing: '#ff9800',
  written: '#4caf50',
  reviewed: '#2196f3',
};
