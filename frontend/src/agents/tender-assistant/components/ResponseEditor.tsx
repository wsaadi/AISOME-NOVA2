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

interface Props {
  chapters: Chapter[];
  onWriteChapter: (chapterId: string, instructions: string) => void;
  onImproveChapter: (chapterId: string, instructions: string) => void;
  onSaveContent: (chapterId: string, content: string) => void;
  onUpdateStructure: (chapters: Chapter[]) => void;
  onGenerateStructure: () => void;
  isLoading: boolean;
  streamingContent: string;
  error?: string | null;
}

const ResponseEditor: React.FC<Props> = ({
  chapters, onWriteChapter, onImproveChapter, onSaveContent, onUpdateStructure,
  onGenerateStructure, isLoading, streamingContent, error,
}) => {
  const [selectedChapterId, setSelectedChapterId] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [aiInstructions, setAiInstructions] = useState('');
  const [previewMode, setPreviewMode] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const selectedChapter = selectedChapterId
    ? findChapter(chapters, selectedChapterId)
    : null;

  // When streaming content arrives, switch to preview mode to show it
  useEffect(() => {
    if (streamingContent && selectedChapterId) {
      setEditMode(false);
      setPreviewMode(true);
    }
  }, [streamingContent, selectedChapterId]);

  // Switch to edit mode with current content
  const startEditing = useCallback(() => {
    if (selectedChapter) {
      setEditContent(selectedChapter.content || '');
      setEditMode(true);
      setPreviewMode(false);
    }
  }, [selectedChapter]);

  const saveEdit = useCallback(() => {
    if (selectedChapterId && editContent !== selectedChapter?.content) {
      onSaveContent(selectedChapterId, editContent);
    }
    setEditMode(false);
    setPreviewMode(true);
  }, [selectedChapterId, editContent, selectedChapter, onSaveContent]);

  const cancelEdit = useCallback(() => {
    setEditMode(false);
    setPreviewMode(true);
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

  const getProgress = () => {
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
    return total > 0 ? Math.round((written / total) * 100) : 0;
  };

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

  return (
    <div style={{ ...styles.editorLayout, padding: 0, height: '100%' }}>
      {/* Chapter tree */}
      <div style={styles.chapterTree}>
        <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--divider-color, #e0e0e0)' }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#888', marginBottom: 4 }}>PROGRESSION</div>
          <div style={styles.progressBar}>
            <div style={{ ...styles.progressFill, width: `${getProgress()}%`, backgroundColor: '#4caf50' }} />
          </div>
          <div style={{ fontSize: 10, color: '#888', textAlign: 'right' as const }}>{getProgress()}%</div>
        </div>

        {chapters.map(ch => (
          <React.Fragment key={ch.id}>
            <button
              style={{
                ...styles.chapterItem,
                ...(selectedChapterId === ch.id ? styles.chapterItemActive : {}),
              }}
              onClick={() => {
                setSelectedChapterId(ch.id);
                setEditMode(false);
                setPreviewMode(true);
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
                  ...(selectedChapterId === sub.id ? styles.chapterItemActive : {}),
                }}
                onClick={() => {
                  setSelectedChapterId(sub.id);
                  setEditMode(false);
                  setPreviewMode(true);
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

      {/* Editor area */}
      <div style={styles.editorArea}>
        {!selectedChapter ? (
          <div style={styles.editorPlaceholder}>
            <div style={{ fontSize: 32, opacity: 0.3 }}>📝</div>
            <p>Sélectionnez un chapitre pour commencer la rédaction</p>
          </div>
        ) : (
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
                    Éditer manuellement
                  </button>
                  <button
                    style={{
                      ...styles.btn, ...styles.btnPrimary, ...styles.btnSmall,
                      ...(isLoading ? styles.btnDisabled : {}),
                    }}
                    onClick={handleWriteChapter}
                    disabled={isLoading}
                  >
                    {selectedChapter.content ? 'Re-générer avec IA' : 'Générer avec IA'}
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
                      Améliorer avec IA
                    </button>
                  )}
                  <div style={{ flex: 1 }} />
                  <input
                    style={{ ...styles.inputField, maxWidth: 350, fontSize: 11 }}
                    placeholder="Instructions pour l'IA (ex: ajouter plus de détails sur...)"
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
                  <MarkdownView content={streamingContent} />
                  <span style={{ display: 'inline-block', width: 8, height: 16, backgroundColor: 'var(--primary-color, #1976d2)', animation: 'blink 1s infinite', marginLeft: 2 }} />
                </div>
              ) : selectedChapter.content ? (
                <div style={styles.markdownContent}>
                  <MarkdownView content={selectedChapter.content} />
                </div>
              ) : (
                <div style={styles.editorPlaceholder}>
                  <p>Aucun contenu rédigé pour ce chapitre.</p>
                  <p style={{ fontSize: 12, color: '#aaa' }}>
                    Utilisez "Générer avec IA" ou "Éditer manuellement" pour commencer.
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
