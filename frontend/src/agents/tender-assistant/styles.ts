/**
 * Styles for the Tender Assistant view.
 *
 * Professional, ergonomic layout with:
 *   - Left navigation sidebar
 *   - Main content area with resizable columns
 *   - Optional right chat panel
 *
 * Uses CSS variables for dark-mode compatibility:
 *   --ta-bg:           main background
 *   --ta-bg-alt:       alternate/card background
 *   --ta-surface:      surface/elevated background
 *   --ta-text:         primary text color
 *   --ta-text-dim:     secondary/dim text color
 *   --ta-border:       default border/divider color
 *   --ta-primary:      accent/primary color
 *   --ta-primary-bg:   very faint accent tint
 */

const SIDEBAR_WIDTH = 240;
const CHAT_WIDTH = 380;

/* ---------- helpers for theme-safe colors ---------- */
const v = (name: string, fallback: string) => `var(${name}, ${fallback})`;

// Main theme tokens — every hard-coded color below references these
const T = {
  bg:        v('--ta-bg', '#ffffff'),
  bgAlt:     v('--ta-bg-alt', '#f7f8fa'),
  surface:   v('--ta-surface', '#fafafa'),
  text:      v('--ta-text', '#1a1a1a'),
  textDim:   v('--ta-text-dim', '#6b7280'),
  border:    v('--ta-border', '#e2e5e9'),
  primary:   v('--ta-primary', '#1976d2'),
  primaryBg: v('--ta-primary-bg', 'rgba(25,118,210,0.06)'),
};

const styles = {
  // ==========================================================================
  // Root layout
  // ==========================================================================
  root: {
    display: 'flex' as const,
    height: '100%',
    overflow: 'hidden' as const,
    fontFamily: '"Inter", "Roboto", "Helvetica Neue", sans-serif',
    backgroundColor: T.bg,
    color: T.text,
  },

  // ==========================================================================
  // Left sidebar
  // ==========================================================================
  sidebar: {
    width: SIDEBAR_WIDTH,
    minWidth: SIDEBAR_WIDTH,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    borderRight: `1px solid ${T.border}`,
    backgroundColor: T.surface,
    overflow: 'hidden' as const,
  },
  sidebarHeader: {
    padding: '16px 16px 12px',
    borderBottom: `1px solid ${T.border}`,
  },
  sidebarTitle: {
    fontSize: 15,
    fontWeight: 700,
    color: T.text,
    margin: 0,
    letterSpacing: '-0.2px',
  },
  sidebarSubtitle: {
    fontSize: 11,
    color: T.textDim,
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
    color: T.textDim,
    transition: 'all 0.15s ease',
    border: 'none' as const,
    background: 'transparent',
    outline: 'none' as const,
    WebkitAppearance: 'none' as any,
    width: '100%',
    textAlign: 'left' as const,
    borderLeft: '3px solid transparent',
  },
  navItemActive: {
    color: T.primary,
    backgroundColor: T.primaryBg,
    borderLeftColor: T.primary,
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
    backgroundColor: T.primary,
    color: '#fff',
    minWidth: 18,
    textAlign: 'center' as const,
  },
  sidebarFooter: {
    padding: '12px 16px',
    borderTop: `1px solid ${T.border}`,
    fontSize: 11,
    color: T.textDim,
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
    backgroundColor: T.bg,
  },
  mainHeader: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    padding: '12px 20px',
    borderBottom: `1px solid ${T.border}`,
    minHeight: 52,
    flexShrink: 0,
  },
  mainTitle: {
    fontSize: 16,
    fontWeight: 700,
    color: T.text,
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
    borderLeft: `1px solid ${T.border}`,
    backgroundColor: T.bg,
  },
  chatPanelCollapsed: {
    width: 0,
    minWidth: 0,
    overflow: 'hidden' as const,
  },
  chatToggle: {
    padding: '4px 10px',
    fontSize: 12,
    fontWeight: 500,
    border: `1px solid ${T.border}`,
    borderRadius: 4,
    background: T.bg,
    cursor: 'pointer' as const,
    color: T.textDim,
    display: 'inline-flex' as const,
    alignItems: 'center' as const,
    gap: 4,
  },
  chatHeader: {
    padding: '12px 16px',
    borderBottom: `1px solid ${T.border}`,
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
  },
  chatTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: T.text,
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
    border: `1px solid ${T.border}`,
    backgroundColor: T.bg,
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
    color: T.text,
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
    color: T.textDim,
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
    backgroundColor: T.bgAlt,
    color: T.textDim,
  },
  docActions: {
    display: 'flex' as const,
    gap: 4,
    marginTop: 10,
    paddingTop: 8,
    borderTop: `1px solid ${T.border}`,
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
    border: `1px solid ${T.border}`,
    backgroundColor: T.bg,
    cursor: 'pointer' as const,
    transition: 'all 0.15s ease',
    fontWeight: 500,
    color: T.textDim,
    outline: 'none' as const,
  },
  filterChipActive: {
    backgroundColor: T.primary,
    borderColor: T.primary,
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
    border: `1px solid ${T.border}`,
    backgroundColor: T.bg,
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
    color: T.text,
    margin: 0,
  },
  comparisonBanner: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 12,
    padding: 16,
    borderRadius: 8,
    backgroundColor: T.primaryBg,
    border: `1px solid ${T.primary}`,
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
    backgroundColor: T.bgAlt,
    border: `1px solid ${T.border}`,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 700,
    margin: 0,
    color: T.text,
  },
  statLabel: {
    fontSize: 11,
    color: T.textDim,
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
    minWidth: 200,
    borderRight: `1px solid ${T.border}`,
    overflow: 'hidden' as const,
    display: 'flex' as const,
    flexDirection: 'column' as const,
    flexShrink: 0,
    backgroundColor: T.surface,
  },
  chapterItem: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 8,
    padding: '8px 12px',
    cursor: 'pointer' as const,
    fontSize: 12,
    color: T.text,
    transition: 'background-color 0.1s ease',
    border: 'none' as const,
    background: 'transparent',
    outline: 'none' as const,
    WebkitAppearance: 'none' as any,
    width: '100%',
    textAlign: 'left' as const,
  },
  chapterItemActive: {
    backgroundColor: T.primaryBg,
    fontWeight: 600,
  },
  chapterNumber: {
    fontSize: 11,
    fontWeight: 700,
    color: T.primary,
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
    backgroundColor: T.bg,
  },
  editorHeader: {
    padding: '12px 16px',
    borderBottom: `1px solid ${T.border}`,
    flexShrink: 0,
  },
  editorChapterTitle: {
    fontSize: 15,
    fontWeight: 600,
    color: T.text,
    margin: 0,
  },
  editorChapterDesc: {
    fontSize: 12,
    color: T.textDim,
    marginTop: 4,
  },
  editorToolbar: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 6,
    padding: '8px 16px',
    borderBottom: `1px solid ${T.border}`,
    flexShrink: 0,
    flexWrap: 'wrap' as const,
    backgroundColor: T.bgAlt,
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
    border: `1px solid ${T.border}`,
    borderRadius: 6,
    resize: 'vertical' as const,
    fontFamily: '"Inter", sans-serif',
    color: T.text,
    backgroundColor: T.bg,
    outline: 'none' as const,
  },
  editorPlaceholder: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    height: '100%',
    color: T.textDim,
    fontSize: 14,
    gap: 8,
  },
  keyPointsList: {
    margin: '8px 0 0',
    padding: '0 0 0 16px',
    fontSize: 12,
    color: T.textDim,
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
    border: `1px solid ${T.border}`,
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
    border: `1px solid ${T.border}`,
  },
  exportLabel: {
    fontSize: 13,
    fontWeight: 600,
    color: T.text,
    marginBottom: 8,
    display: 'block' as const,
  },
  exportInput: {
    width: '100%',
    padding: '8px 12px',
    fontSize: 13,
    border: `1px solid ${T.border}`,
    borderRadius: 4,
    color: T.text,
    backgroundColor: T.bg,
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
    border: `1px solid ${T.border}`,
    backgroundColor: T.bg,
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
    color: T.text,
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
    color: T.textDim,
    marginTop: 6,
    lineHeight: 1.5,
  },
  addForm: {
    padding: 16,
    borderRadius: 8,
    border: `2px dashed ${T.border}`,
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
    border: `1px solid ${T.border}`,
    borderRadius: 4,
    outline: 'none' as const,
    color: T.text,
    backgroundColor: T.bg,
  },
  selectField: {
    padding: '8px 10px',
    fontSize: 13,
    border: `1px solid ${T.border}`,
    borderRadius: 4,
    outline: 'none' as const,
    color: T.text,
    backgroundColor: T.bg,
  },

  // ==========================================================================
  // Buttons — always explicit background, no browser-default gray
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
    backgroundColor: T.bg,  // explicit default — never browser gray
    color: T.text,
    outline: 'none' as const,
  },
  btnPrimary: {
    backgroundColor: T.primary,
    color: '#fff',
  },
  btnSecondary: {
    backgroundColor: T.bgAlt,
    color: T.text,
    border: `1px solid ${T.border}`,
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
    color: T.text,
    margin: '0 0 8px',
  },
  helpText: {
    fontSize: 12,
    color: T.textDim,
    margin: '0 0 12px',
    lineHeight: 1.5,
  },
  emptyState: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    padding: 40,
    color: T.textDim,
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
    backgroundColor: T.border,
    margin: '16px 0',
  },
  progressBar: {
    height: 4,
    borderRadius: 2,
    backgroundColor: T.bgAlt,
    overflow: 'hidden' as const,
    margin: '8px 0',
  },
  progressFill: {
    height: '100%',
    borderRadius: 2,
    backgroundColor: T.primary,
    transition: 'width 0.3s ease',
  },
  progressText: {
    fontSize: 11,
    color: T.textDim,
    textAlign: 'center' as const,
  },
  markdownContent: {
    fontSize: 13,
    lineHeight: 1.7,
    color: T.text,
  },

  // ==========================================================================
  // Resize handle (drag to resize columns)
  // ==========================================================================
  resizeHandle: {
    width: 5,
    cursor: 'col-resize' as const,
    backgroundColor: 'transparent',
    transition: 'background-color 0.15s ease',
    flexShrink: 0,
    zIndex: 10,
    '&:hover': { backgroundColor: T.primary },
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
