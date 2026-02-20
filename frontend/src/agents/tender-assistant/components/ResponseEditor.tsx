import React, { useState, useCallback, useEffect, useRef } from 'react';
import { MarkdownView } from 'framework/components';
import styles, { STATUS_COLORS } from '../styles';

interface Chapter {
  id: string;
  number: string;
  title: string;
  description: string;
  requirements_covered: string[];
  key_points: string[];
  estimated_pages: number;
  content: string;
  status: string;
  lastModified?: string;
  sub_chapters: Chapter[];
}

interface PseudonymEntry {
  id: string;
  placeholder: string;
  real: string;
  category: string;
}

interface Props {
  chapters: Chapter[];
  onWriteChapter: (chapterId: string, instructions: string) => void;
  onImproveChapter: (chapterId: string, instructions: string) => void;
  onWriteAll: () => void;
  onImproveAll: () => void;
  onSaveContent: (chapterId: string, content: string) => void;
  onUpdateStructure: (chapters: Chapter[]) => void;
  onGenerateStructure: () => void;
  isLoading: boolean;
  streamingContent: string;
  error?: string | null;
  pseudonyms?: PseudonymEntry[];
}

type ViewMode = 'editor' | 'full-preview' | 'structure';

/** Replace pseudonym placeholders with real values for display */
const depseudonymize = (text: string, pseudonyms: PseudonymEntry[]): string => {
  if (!pseudonyms || pseudonyms.length === 0) return text;
  let result = text;
  for (const entry of pseudonyms) {
    if (entry.placeholder && entry.real) {
      result = result.split(entry.placeholder).join(entry.real);
    }
  }
  return result;
};

/**
 * Strip duplicate headings from AI-generated chapter content.
 * The AI often generates its own heading (e.g. "# 1. Introduction") which
 * conflicts with the heading we add in buildFullDocument(). This strips the
 * first line if it looks like a markdown heading that repeats the chapter title.
 */
const stripLeadingHeading = (content: string, chapterTitle: string): string => {
  const lines = content.split('\n');
  if (lines.length === 0) return content;
  const first = lines[0].trim();
  // Match lines like "# 1. Title", "## 1.2. Title", "# Title", "## Title"
  if (/^#{1,4}\s+/.test(first)) {
    const headingText = first.replace(/^#{1,4}\s+/, '').replace(/^\d+(\.\d+)*\.?\s*/, '').trim().toLowerCase();
    const titleNorm = chapterTitle.trim().toLowerCase();
    // If the heading text is the chapter title (or very close), strip it
    if (headingText === titleNorm || titleNorm.startsWith(headingText) || headingText.startsWith(titleNorm)) {
      const rest = lines.slice(1).join('\n').replace(/^\n+/, '');
      return rest;
    }
  }
  return content;
};

const ResponseEditor: React.FC<Props> = ({
  chapters, onWriteChapter, onImproveChapter, onWriteAll, onImproveAll,
  onSaveContent, onUpdateStructure, onGenerateStructure, isLoading, streamingContent,
  error, pseudonyms = [],
}) => {
  const [selectedChapterId, setSelectedChapterId] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [aiInstructions, setAiInstructions] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('editor');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Structure editing state
  const [editingChapter, setEditingChapter] = useState<{ id: string; field: 'title' | 'description'; parentId?: string } | null>(null);
  const [editingValue, setEditingValue] = useState('');
  const [addingChapter, setAddingChapter] = useState<{ parentId?: string } | null>(null);
  const [newChapterTitle, setNewChapterTitle] = useState('');
  const [treeWidth, setTreeWidth] = useState(280);

  // Resizable chapter tree handle
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = treeWidth;
    const onMove = (ev: MouseEvent) => {
      const delta = ev.clientX - startX;
      setTreeWidth(Math.max(180, Math.min(500, startW + delta)));
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [treeWidth]);

  const selectedChapter = selectedChapterId
    ? findChapter(chapters, selectedChapterId)
    : null;

  useEffect(() => {
    if (streamingContent && selectedChapterId) {
      setEditMode(false);
    }
  }, [streamingContent, selectedChapterId]);

  const startEditing = useCallback(() => {
    if (selectedChapter) {
      setEditContent(selectedChapter.content || '');
      setEditMode(true);
    }
  }, [selectedChapter]);

  const saveEdit = useCallback(() => {
    if (selectedChapterId && editContent !== selectedChapter?.content) {
      onSaveContent(selectedChapterId, editContent);
    }
    setEditMode(false);
  }, [selectedChapterId, editContent, selectedChapter, onSaveContent]);

  const cancelEdit = useCallback(() => {
    setEditMode(false);
  }, []);

  const handleWriteChapter = () => {
    if (selectedChapterId) {
      onWriteChapter(selectedChapterId, aiInstructions);
      setAiInstructions('');
    }
  };

  const handleImproveChapter = () => {
    if (selectedChapterId && aiInstructions.trim()) {
      onImproveChapter(selectedChapterId, aiInstructions);
      setAiInstructions('');
    }
  };

  const getStatusColor = (status: string) => STATUS_COLORS[status] || STATUS_COLORS.draft;

  const getStats = () => {
    let total = 0;
    let written = 0;
    const count = (chs: Chapter[]) => {
      for (const ch of chs) {
        total++;
        if (ch.content) written++;
        count(ch.sub_chapters || []);
      }
    };
    count(chapters);
    return { total, written, unwritten: total - written };
  };

  const stats = getStats();
  const getProgress = () => stats.total > 0 ? Math.round((stats.written / stats.total) * 100) : 0;

  // ── Structure management ────────────────────────────────────────────

  const addChapter = (parentId?: string) => {
    if (!newChapterTitle.trim()) return;
    let updated: Chapter[];
    if (!parentId) {
      const num = String(chapters.length + 1);
      updated = [...chapters, {
        id: `ch-${Date.now()}`,
        number: num,
        title: newChapterTitle.trim(),
        description: '',
        requirements_covered: [],
        key_points: [],
        estimated_pages: 2,
        content: '',
        status: 'draft',
        sub_chapters: [],
      }];
    } else {
      updated = chapters.map(ch => {
        if (ch.id === parentId) {
          const subNum = `${ch.number}.${(ch.sub_chapters || []).length + 1}`;
          return {
            ...ch,
            sub_chapters: [...(ch.sub_chapters || []), {
              id: `sub-${Date.now()}`,
              number: subNum,
              title: newChapterTitle.trim(),
              description: '',
              requirements_covered: [],
              key_points: [],
              estimated_pages: 1,
              content: '',
              status: 'draft',
              sub_chapters: [],
            }],
          };
        }
        return ch;
      });
    }
    onUpdateStructure(updated);
    setAddingChapter(null);
    setNewChapterTitle('');
  };

  const deleteChapter = (id: string) => {
    // Try top-level first
    let found = chapters.some(ch => ch.id === id);
    let updated: Chapter[];
    if (found) {
      updated = chapters.filter(ch => ch.id !== id).map((ch, i) => ({
        ...ch,
        number: String(i + 1),
        sub_chapters: (ch.sub_chapters || []).map((sub, j) => ({
          ...sub,
          number: `${i + 1}.${j + 1}`,
        })),
      }));
    } else {
      updated = chapters.map((ch, ci) => ({
        ...ch,
        sub_chapters: (ch.sub_chapters || [])
          .filter(sub => sub.id !== id)
          .map((sub, j) => ({ ...sub, number: `${ch.number}.${j + 1}` })),
      }));
    }
    onUpdateStructure(updated);
    if (selectedChapterId === id) setSelectedChapterId(null);
  };

  const saveChapterField = () => {
    if (!editingChapter || !editingValue.trim()) {
      setEditingChapter(null);
      return;
    }
    const updated = chapters.map(ch => {
      if (ch.id === editingChapter.id) {
        return { ...ch, [editingChapter.field]: editingValue.trim() };
      }
      return {
        ...ch,
        sub_chapters: (ch.sub_chapters || []).map(sub =>
          sub.id === editingChapter.id
            ? { ...sub, [editingChapter.field]: editingValue.trim() }
            : sub
        ),
      };
    });
    onUpdateStructure(updated);
    setEditingChapter(null);
    setEditingValue('');
  };

  const moveChapter = (id: string, direction: 'up' | 'down') => {
    const idx = chapters.findIndex(ch => ch.id === id);
    if (idx === -1) {
      // Sub-chapter move
      const updated = chapters.map(ch => {
        const subIdx = (ch.sub_chapters || []).findIndex(s => s.id === id);
        if (subIdx === -1) return ch;
        const subs = [...ch.sub_chapters];
        const swapIdx = direction === 'up' ? subIdx - 1 : subIdx + 1;
        if (swapIdx < 0 || swapIdx >= subs.length) return ch;
        [subs[subIdx], subs[swapIdx]] = [subs[swapIdx], subs[subIdx]];
        return {
          ...ch,
          sub_chapters: subs.map((s, j) => ({ ...s, number: `${ch.number}.${j + 1}` })),
        };
      });
      onUpdateStructure(updated);
      return;
    }
    const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= chapters.length) return;
    const updated = [...chapters];
    [updated[idx], updated[swapIdx]] = [updated[swapIdx], updated[idx]];
    onUpdateStructure(updated.map((ch, i) => ({
      ...ch,
      number: String(i + 1),
      sub_chapters: (ch.sub_chapters || []).map((sub, j) => ({
        ...sub,
        number: `${i + 1}.${j + 1}`,
      })),
    })));
  };

  // ── Full document builder ───────────────────────────────────────────

  const buildFullDocument = (): string => {
    const parts: string[] = [];
    for (const ch of chapters) {
      parts.push(`# ${ch.number}. ${ch.title}`);
      if (ch.content) {
        parts.push(stripLeadingHeading(ch.content, ch.title));
      } else {
        parts.push('*Contenu non rédigé*');
      }
      parts.push('');
      for (const sub of ch.sub_chapters || []) {
        parts.push(`## ${sub.number}. ${sub.title}`);
        if (sub.content) {
          parts.push(stripLeadingHeading(sub.content, sub.title));
        } else {
          parts.push('*Contenu non rédigé*');
        }
        parts.push('');
      }
    }
    return depseudonymize(parts.join('\n\n'), pseudonyms);
  };

  // ── Empty state ─────────────────────────────────────────────────────

  if (chapters.length === 0) {
    return (
      <div style={styles.emptyState}>
        <div style={styles.emptyIcon}>📝</div>
        <p style={styles.emptyText}>
          Aucune structure de réponse définie.
        </p>
        <p style={{ fontSize: 12, color: '#999', marginBottom: 16 }}>
          Générez automatiquement la structure des chapitres à partir de vos documents analysés.
        </p>
        {error && (
          <div style={{
            padding: '10px 16px',
            marginBottom: 16,
            borderRadius: 6,
            backgroundColor: '#ffebee',
            border: '1px solid #ef9a9a',
            color: '#c62828',
            fontSize: 12,
            maxWidth: 500,
            textAlign: 'left' as const,
          }}>
            <strong>Erreur :</strong> {error}
          </div>
        )}
        <button
          style={{
            ...styles.btn,
            ...styles.btnPrimary,
            padding: '10px 24px',
            fontSize: 14,
            ...(isLoading ? styles.btnDisabled : {}),
          }}
          onClick={onGenerateStructure}
          disabled={isLoading}
        >
          {isLoading ? 'Génération en cours...' : 'Générer la structure'}
        </button>
      </div>
    );
  }

  // ── Main layout ─────────────────────────────────────────────────────

  return (
    <div style={{ ...styles.editorLayout, padding: 0, height: '100%' }}>
      {/* Chapter tree */}
      <div style={{ ...styles.chapterTree, width: treeWidth, minWidth: treeWidth }}>
        {/* View mode tabs */}
        <div style={{ display: 'flex', borderBottom: `1px solid var(--ta-border, #e0e0e0)` }}>
          {([
            ['editor', 'Rédaction'],
            ['full-preview', 'Aperçu'],
            ['structure', 'Structure'],
          ] as [ViewMode, string][]).map(([mode, label]) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              style={{
                flex: 1,
                padding: '8px 4px',
                fontSize: 10,
                fontWeight: viewMode === mode ? 700 : 500,
                color: viewMode === mode ? 'var(--ta-primary, #1976d2)' : 'var(--ta-text-dim, #888)',
                background: viewMode === mode ? 'var(--ta-primary-bg, rgba(25,118,210,0.06))' : 'transparent',
                border: 'none',
                borderBottom: viewMode === mode ? '2px solid var(--ta-primary, #1976d2)' : '2px solid transparent',
                cursor: 'pointer',
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Progress + bulk actions */}
        <div style={{ padding: '8px 12px', borderBottom: `1px solid var(--ta-border, #e0e0e0)` }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ta-text-dim, #888)', marginBottom: 4 }}>PROGRESSION</div>
          <div style={styles.progressBar}>
            <div style={{ ...styles.progressFill, width: `${getProgress()}%`, backgroundColor: '#4caf50' }} />
          </div>
          <div style={{ fontSize: 10, color: '#888', textAlign: 'right' as const, marginBottom: 6 }}>
            {stats.written}/{stats.total} chapitres · {getProgress()}%
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            {stats.unwritten > 0 && (
              <button
                style={{
                  flex: 1, padding: '5px 4px', fontSize: 10, fontWeight: 600,
                  border: 'none', borderRadius: 4, cursor: isLoading ? 'not-allowed' : 'pointer',
                  backgroundColor: '#1976d2', color: '#fff',
                  opacity: isLoading ? 0.5 : 1,
                }}
                onClick={onWriteAll}
                disabled={isLoading}
                title={`Rédiger les ${stats.unwritten} chapitres non rédigés`}
              >
                Rédiger tout ({stats.unwritten})
              </button>
            )}
            {stats.written > 0 && (
              <button
                style={{
                  flex: 1, padding: '5px 4px', fontSize: 10, fontWeight: 600,
                  border: 'none', borderRadius: 4, cursor: isLoading ? 'not-allowed' : 'pointer',
                  backgroundColor: '#7b1fa2', color: '#fff',
                  opacity: isLoading ? 0.5 : 1,
                }}
                onClick={onImproveAll}
                disabled={isLoading}
                title={`Améliorer les ${stats.written} chapitres rédigés`}
              >
                Améliorer tout ({stats.written})
              </button>
            )}
          </div>
        </div>

        {/* Chapter list */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {chapters.map((ch, ci) => (
            <React.Fragment key={ch.id}>
              <button
                style={{
                  ...styles.chapterItem,
                  ...(selectedChapterId === ch.id && viewMode === 'editor' ? styles.chapterItemActive : {}),
                }}
                onClick={() => {
                  setSelectedChapterId(ch.id);
                  setEditMode(false);
                  if (viewMode !== 'editor') setViewMode('editor');
                }}
              >
                <span style={styles.chapterNumber}>{ch.number}</span>
                <span style={styles.chapterTitle} title={ch.title}>{ch.title}</span>
                <span style={{ ...styles.chapterStatus, backgroundColor: getStatusColor(ch.status || (ch.content ? 'written' : 'draft')) }} />
              </button>

              {(ch.sub_chapters || []).map(sub => (
                <button
                  key={sub.id}
                  style={{
                    ...styles.chapterItem,
                    ...styles.subChapter,
                    ...(selectedChapterId === sub.id && viewMode === 'editor' ? styles.chapterItemActive : {}),
                  }}
                  onClick={() => {
                    setSelectedChapterId(sub.id);
                    setEditMode(false);
                    if (viewMode !== 'editor') setViewMode('editor');
                  }}
                >
                  <span style={{ ...styles.chapterNumber, fontSize: 10 }}>{sub.number}</span>
                  <span style={styles.chapterTitle} title={sub.title}>{sub.title}</span>
                  <span style={{ ...styles.chapterStatus, backgroundColor: getStatusColor(sub.status || (sub.content ? 'written' : 'draft')) }} />
                </button>
              ))}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Resize handle */}
      <div
        className="ta-resize-handle"
        onMouseDown={handleResizeStart}
        style={{ width: 5, cursor: 'col-resize', flexShrink: 0, zIndex: 10 }}
      />

      {/* ── Right panel: depends on viewMode ─────────────────────── */}
      <div style={styles.editorArea}>
        {viewMode === 'full-preview' && (
          <FullPreviewPanel chapters={chapters} buildFullDocument={buildFullDocument} />
        )}

        {viewMode === 'structure' && (
          <StructurePanel
            chapters={chapters}
            editingChapter={editingChapter}
            editingValue={editingValue}
            addingChapter={addingChapter}
            newChapterTitle={newChapterTitle}
            onStartEditing={(id, field, value) => { setEditingChapter({ id, field }); setEditingValue(value); }}
            onEditingValueChange={setEditingValue}
            onSaveField={saveChapterField}
            onCancelEditing={() => setEditingChapter(null)}
            onAddChapter={addChapter}
            onStartAdding={(parentId) => { setAddingChapter({ parentId }); setNewChapterTitle(''); }}
            onCancelAdding={() => setAddingChapter(null)}
            onNewTitleChange={setNewChapterTitle}
            onDelete={deleteChapter}
            onMove={moveChapter}
          />
        )}

        {viewMode === 'editor' && !selectedChapter && (
          <div style={styles.editorPlaceholder}>
            <div style={{ fontSize: 32, opacity: 0.3 }}>📝</div>
            <p>Sélectionnez un chapitre pour commencer la rédaction</p>
          </div>
        )}

        {viewMode === 'editor' && selectedChapter && (
          <>
            {/* Chapter header */}
            <div style={styles.editorHeader}>
              <h3 style={styles.editorChapterTitle}>
                {selectedChapter.number} — {selectedChapter.title}
              </h3>
              {selectedChapter.description && (
                <p style={styles.editorChapterDesc}>{selectedChapter.description}</p>
              )}
              {selectedChapter.key_points && selectedChapter.key_points.length > 0 && (
                <ul style={styles.keyPointsList}>
                  {selectedChapter.key_points.map((kp, i) => (
                    <li key={i}>{kp}</li>
                  ))}
                </ul>
              )}
            </div>

            {/* Toolbar */}
            <div style={styles.editorToolbar}>
              {!editMode ? (
                <>
                  <button
                    style={{ ...styles.btn, ...styles.btnSecondary, ...styles.btnSmall }}
                    onClick={startEditing}
                  >
                    Éditer
                  </button>
                  <button
                    style={{
                      ...styles.btn, ...styles.btnPrimary, ...styles.btnSmall,
                      ...(isLoading ? styles.btnDisabled : {}),
                    }}
                    onClick={handleWriteChapter}
                    disabled={isLoading}
                  >
                    {selectedChapter.content ? 'Re-générer' : 'Générer avec IA'}
                  </button>
                  {selectedChapter.content && (
                    <button
                      style={{
                        ...styles.btn, ...styles.btnSmall,
                        backgroundColor: '#7b1fa2', color: '#fff',
                        ...(isLoading || !aiInstructions.trim() ? styles.btnDisabled : {}),
                      }}
                      onClick={handleImproveChapter}
                      disabled={isLoading || !aiInstructions.trim()}
                    >
                      Améliorer
                    </button>
                  )}
                  <div style={{ flex: 1 }} />
                  <input
                    style={{ ...styles.inputField, maxWidth: 350, fontSize: 11 }}
                    placeholder="Instructions pour l'IA..."
                    value={aiInstructions}
                    onChange={e => setAiInstructions(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        if (selectedChapter.content && aiInstructions.trim()) {
                          handleImproveChapter();
                        } else {
                          handleWriteChapter();
                        }
                      }
                    }}
                  />
                </>
              ) : (
                <>
                  <button
                    style={{ ...styles.btn, ...styles.btnPrimary, ...styles.btnSmall }}
                    onClick={saveEdit}
                  >
                    Sauvegarder
                  </button>
                  <button
                    style={{ ...styles.btn, ...styles.btnSecondary, ...styles.btnSmall }}
                    onClick={cancelEdit}
                  >
                    Annuler
                  </button>
                  <div style={{ flex: 1 }} />
                  <span style={{ fontSize: 11, color: '#888' }}>Mode édition manuelle</span>
                </>
              )}
            </div>

            {/* Content */}
            <div style={styles.editorContent}>
              {editMode ? (
                <textarea
                  ref={textareaRef}
                  style={styles.textarea}
                  value={editContent}
                  onChange={e => setEditContent(e.target.value)}
                  placeholder="Rédigez le contenu de ce chapitre en markdown..."
                />
              ) : streamingContent && isLoading ? (
                <div style={styles.markdownContent}>
                  <MarkdownView content={depseudonymize(streamingContent, pseudonyms)} />
                  <span style={{ display: 'inline-block', width: 8, height: 16, backgroundColor: 'var(--primary-color, #1976d2)', animation: 'blink 1s infinite', marginLeft: 2 }} />
                </div>
              ) : selectedChapter.content ? (
                <div style={styles.markdownContent}>
                  <MarkdownView content={depseudonymize(selectedChapter.content, pseudonyms)} />
                </div>
              ) : (
                <div style={styles.editorPlaceholder}>
                  <p>Aucun contenu rédigé pour ce chapitre.</p>
                  <p style={{ fontSize: 12, color: '#aaa' }}>
                    Utilisez "Générer avec IA" ou "Éditer" pour commencer.
                  </p>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════
// Full Preview Panel
// ═══════════════════════════════════════════════════════════════════════

const FullPreviewPanel: React.FC<{
  chapters: Chapter[];
  buildFullDocument: () => string;
}> = ({ chapters, buildFullDocument }) => {
  const fullDoc = buildFullDocument();
  const wordCount = fullDoc.split(/\s+/).filter(Boolean).length;
  const pageEstimate = Math.ceil(wordCount / 300);

  return (
    <div style={{ display: 'flex', flexDirection: 'column' as const, height: '100%' }}>
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--divider-color, #e0e0e0)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}>
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: 'var(--text-primary, #333)' }}>
          Aperçu du document complet
        </h3>
        <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#888' }}>
          <span>{chapters.length} chapitres</span>
          <span>{wordCount} mots</span>
          <span>~{pageEstimate} pages</span>
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '20px 32px' }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <MarkdownView content={fullDoc} />
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════
// Structure Panel
// ═══════════════════════════════════════════════════════════════════════

interface StructurePanelProps {
  chapters: Chapter[];
  editingChapter: { id: string; field: 'title' | 'description' } | null;
  editingValue: string;
  addingChapter: { parentId?: string } | null;
  newChapterTitle: string;
  onStartEditing: (id: string, field: 'title' | 'description', value: string) => void;
  onEditingValueChange: (val: string) => void;
  onSaveField: () => void;
  onCancelEditing: () => void;
  onAddChapter: (parentId?: string) => void;
  onStartAdding: (parentId?: string) => void;
  onCancelAdding: () => void;
  onNewTitleChange: (val: string) => void;
  onDelete: (id: string) => void;
  onMove: (id: string, dir: 'up' | 'down') => void;
}

const StructurePanel: React.FC<StructurePanelProps> = ({
  chapters, editingChapter, editingValue, addingChapter, newChapterTitle,
  onStartEditing, onEditingValueChange, onSaveField, onCancelEditing,
  onAddChapter, onStartAdding, onCancelAdding, onNewTitleChange,
  onDelete, onMove,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column' as const, height: '100%' }}>
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--divider-color, #e0e0e0)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}>
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>
          Gestion de la structure
        </h3>
        <button
          style={{ ...styles.btn, ...styles.btnPrimary, ...styles.btnSmall }}
          onClick={() => onStartAdding(undefined)}
        >
          + Ajouter un chapitre
        </button>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {/* Add top-level form */}
        {addingChapter && !addingChapter.parentId && (
          <AddChapterForm
            value={newChapterTitle}
            onChange={onNewTitleChange}
            onConfirm={() => onAddChapter(undefined)}
            onCancel={onCancelAdding}
            placeholder="Titre du nouveau chapitre"
          />
        )}

        {chapters.map((ch, ci) => (
          <div key={ch.id} style={{
            marginBottom: 12,
            border: '1px solid var(--divider-color, #e0e0e0)',
            borderRadius: 8,
            overflow: 'hidden',
          }}>
            {/* Chapter header */}
            <div style={{
              padding: '10px 14px',
              backgroundColor: 'var(--bg-color, #fafafa)',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}>
              <span style={{ fontWeight: 700, color: 'var(--primary-color, #1976d2)', fontSize: 13, minWidth: 24 }}>
                {ch.number}
              </span>

              {editingChapter?.id === ch.id && editingChapter.field === 'title' ? (
                <input
                  autoFocus
                  style={{ ...styles.inputField, fontSize: 13, fontWeight: 600, flex: 1 }}
                  value={editingValue}
                  onChange={e => onEditingValueChange(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') onSaveField(); if (e.key === 'Escape') onCancelEditing(); }}
                  onBlur={onSaveField}
                />
              ) : (
                <span
                  style={{ flex: 1, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}
                  onClick={() => onStartEditing(ch.id, 'title', ch.title)}
                  title="Cliquer pour modifier"
                >
                  {ch.title}
                </span>
              )}

              <div style={{ display: 'flex', gap: 2 }}>
                <IconBtn title="Monter" onClick={() => onMove(ch.id, 'up')} disabled={ci === 0}>&#x25B2;</IconBtn>
                <IconBtn title="Descendre" onClick={() => onMove(ch.id, 'down')} disabled={ci === chapters.length - 1}>&#x25BC;</IconBtn>
                <IconBtn title="Ajouter sous-chapitre" onClick={() => onStartAdding(ch.id)}>+</IconBtn>
                <IconBtn title="Supprimer" onClick={() => { if (window.confirm(`Supprimer "${ch.title}" ?`)) onDelete(ch.id); }} danger>&#x2715;</IconBtn>
              </div>
            </div>

            {/* Description */}
            <div style={{ padding: '6px 14px 6px 46px' }}>
              {editingChapter?.id === ch.id && editingChapter.field === 'description' ? (
                <input
                  autoFocus
                  style={{ ...styles.inputField, fontSize: 11, width: '100%' }}
                  value={editingValue}
                  onChange={e => onEditingValueChange(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') onSaveField(); if (e.key === 'Escape') onCancelEditing(); }}
                  onBlur={onSaveField}
                />
              ) : (
                <p
                  style={{ margin: 0, fontSize: 11, color: '#888', cursor: 'pointer', minHeight: 16 }}
                  onClick={() => onStartEditing(ch.id, 'description', ch.description || '')}
                  title="Cliquer pour modifier la description"
                >
                  {ch.description || 'Ajouter une description...'}
                </p>
              )}
            </div>

            {/* Sub-chapters */}
            {(ch.sub_chapters || []).map((sub, si) => (
              <div key={sub.id} style={{
                padding: '8px 14px 8px 46px',
                borderTop: '1px solid var(--divider-color, #f0f0f0)',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}>
                <span style={{ fontWeight: 600, color: 'var(--primary-color, #1976d2)', fontSize: 11, minWidth: 32 }}>
                  {sub.number}
                </span>
                {editingChapter?.id === sub.id && editingChapter.field === 'title' ? (
                  <input
                    autoFocus
                    style={{ ...styles.inputField, fontSize: 12, flex: 1 }}
                    value={editingValue}
                    onChange={e => onEditingValueChange(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') onSaveField(); if (e.key === 'Escape') onCancelEditing(); }}
                    onBlur={onSaveField}
                  />
                ) : (
                  <span
                    style={{ flex: 1, fontSize: 12, cursor: 'pointer' }}
                    onClick={() => onStartEditing(sub.id, 'title', sub.title)}
                    title="Cliquer pour modifier"
                  >
                    {sub.title}
                  </span>
                )}
                <div style={{ display: 'flex', gap: 2 }}>
                  <IconBtn title="Monter" onClick={() => onMove(sub.id, 'up')} disabled={si === 0}>&#x25B2;</IconBtn>
                  <IconBtn title="Descendre" onClick={() => onMove(sub.id, 'down')} disabled={si === (ch.sub_chapters || []).length - 1}>&#x25BC;</IconBtn>
                  <IconBtn title="Supprimer" onClick={() => { if (window.confirm(`Supprimer "${sub.title}" ?`)) onDelete(sub.id); }} danger>&#x2715;</IconBtn>
                </div>
              </div>
            ))}

            {/* Add sub-chapter form */}
            {addingChapter?.parentId === ch.id && (
              <div style={{ padding: '8px 14px 8px 46px', borderTop: '1px solid var(--divider-color, #f0f0f0)' }}>
                <AddChapterForm
                  value={newChapterTitle}
                  onChange={onNewTitleChange}
                  onConfirm={() => onAddChapter(ch.id)}
                  onCancel={onCancelAdding}
                  placeholder="Titre du sous-chapitre"
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════
// Small reusable components
// ═══════════════════════════════════════════════════════════════════════

const IconBtn: React.FC<{
  onClick: () => void;
  title: string;
  disabled?: boolean;
  danger?: boolean;
  children: React.ReactNode;
}> = ({ onClick, title, disabled, danger, children }) => (
  <button
    title={title}
    onClick={onClick}
    disabled={disabled}
    style={{
      width: 22,
      height: 22,
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      border: 'none',
      borderRadius: 4,
      background: 'none',
      cursor: disabled ? 'default' : 'pointer',
      fontSize: 11,
      color: danger ? '#d32f2f' : '#888',
      opacity: disabled ? 0.3 : 1,
    }}
  >
    {children}
  </button>
);

const AddChapterForm: React.FC<{
  value: string;
  onChange: (val: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
  placeholder: string;
}> = ({ value, onChange, onConfirm, onCancel, placeholder }) => (
  <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 10 }}>
    <input
      autoFocus
      style={{ ...styles.inputField, fontSize: 12, flex: 1 }}
      placeholder={placeholder}
      value={value}
      onChange={e => onChange(e.target.value)}
      onKeyDown={e => { if (e.key === 'Enter') onConfirm(); if (e.key === 'Escape') onCancel(); }}
    />
    <button style={{ ...styles.btn, ...styles.btnPrimary, ...styles.btnSmall }} onClick={onConfirm}>OK</button>
    <button style={{ ...styles.btn, ...styles.btnSecondary, ...styles.btnSmall }} onClick={onCancel}>Annuler</button>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════

function findChapter(chapters: Chapter[], id: string): Chapter | null {
  for (const ch of chapters) {
    if (ch.id === id) return ch;
    for (const sub of ch.sub_chapters || []) {
      if (sub.id === id) return sub;
    }
  }
  return null;
}

export default ResponseEditor;
