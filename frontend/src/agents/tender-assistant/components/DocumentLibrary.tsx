import React, { useState, useCallback } from 'react';
import { FileUpload, ActionButton } from 'framework/components';
import styles, { CATEGORY_COLORS } from '../styles';

interface DocumentImage {
  key: string;
  name: string;
  contentType: string;
  size: number;
}

interface Document {
  id: string;
  fileKey: string;
  fileName: string;
  category: string;
  tags: string[];
  uploadedAt: string;
  analyzed: boolean;
  textLength?: number;
  images?: DocumentImage[];
}

interface Props {
  documents: Document[];
  onUpload: (file: File, category: string, tags: string[]) => Promise<void>;
  onDelete: (docId: string) => void;
  onAnalyze: (docId: string) => void;
  onUpdateMeta: (docId: string, category: string, tags: string[]) => void;
  isLoading: boolean;
  progress: number;
  progressMessage: string;
}

const CATEGORIES = [
  { value: 'all', label: 'Tous' },
  { value: 'ancien_ao', label: 'Ancien AO' },
  { value: 'nouvel_ao', label: 'Nouvel AO' },
  { value: 'ancienne_reponse', label: 'Ancienne réponse' },
  { value: 'template', label: 'Template' },
  { value: 'other', label: 'Autre' },
];

const DocumentLibrary: React.FC<Props> = ({
  documents, onUpload, onDelete, onAnalyze, onUpdateMeta, isLoading, progress, progressMessage,
}) => {
  const [filter, setFilter] = useState('all');
  const [uploadCategory, setUploadCategory] = useState('nouvel_ao');
  const [uploadTags, setUploadTags] = useState('');
  const [editingDoc, setEditingDoc] = useState<string | null>(null);
  const [editCategory, setEditCategory] = useState('');
  const [editTags, setEditTags] = useState('');

  const filteredDocs = filter === 'all' ? documents : documents.filter(d => d.category === filter);

  const handleUpload = useCallback(async (file: File) => {
    const tags = uploadTags.split(',').map(t => t.trim()).filter(Boolean);
    await onUpload(file, uploadCategory, tags);
    setUploadTags('');
    return '';
  }, [onUpload, uploadCategory, uploadTags]);

  const startEdit = (doc: Document) => {
    setEditingDoc(doc.id);
    setEditCategory(doc.category);
    setEditTags(doc.tags.join(', '));
  };

  const saveEdit = (docId: string) => {
    const tags = editTags.split(',').map(t => t.trim()).filter(Boolean);
    onUpdateMeta(docId, editCategory, tags);
    setEditingDoc(null);
  };

  const getCategoryStyle = (cat: string) => {
    const colors = CATEGORY_COLORS[cat] || CATEGORY_COLORS.other;
    return { backgroundColor: colors.bg, color: colors.text };
  };

  const countByCategory = (cat: string) => documents.filter(d => d.category === cat).length;

  return (
    <div>
      {/* Upload section */}
      <div style={styles.uploadArea}>
        <div style={{ ...styles.formRow, marginBottom: 8 }}>
          <select
            style={styles.selectField}
            value={uploadCategory}
            onChange={e => setUploadCategory(e.target.value)}
          >
            {CATEGORIES.filter(c => c.value !== 'all').map(c => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
          <input
            style={styles.inputField}
            placeholder="Tags (séparés par des virgules)"
            value={uploadTags}
            onChange={e => setUploadTags(e.target.value)}
          />
        </div>
        <FileUpload
          onUpload={handleUpload}
          accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.csv,.txt"
          label="Sélectionner des documents (PDF, Word, Excel, PowerPoint, CSV, TXT)"
          multiple
          disabled={isLoading}
        />
        {progress > 0 && progress < 100 && (
          <div>
            <div style={styles.progressBar}>
              <div style={{ ...styles.progressFill, width: `${progress}%` }} />
            </div>
            <p style={styles.progressText}>{progressMessage}</p>
          </div>
        )}
      </div>

      {/* Filter bar */}
      <div style={styles.filterBar}>
        {CATEGORIES.map(cat => (
          <button
            key={cat.value}
            style={{
              ...styles.filterChip,
              ...(filter === cat.value ? styles.filterChipActive : {}),
            }}
            onClick={() => setFilter(cat.value)}
          >
            {cat.label}
            {cat.value !== 'all' && ` (${countByCategory(cat.value)})`}
            {cat.value === 'all' && ` (${documents.length})`}
          </button>
        ))}
      </div>

      {/* Document grid */}
      {filteredDocs.length === 0 ? (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>📁</div>
          <p style={styles.emptyText}>
            {filter === 'all'
              ? 'Aucun document chargé. Uploadez vos documents pour commencer.'
              : `Aucun document dans la catégorie "${CATEGORIES.find(c => c.value === filter)?.label}".`}
          </p>
        </div>
      ) : (
        <div style={styles.docGrid}>
          {filteredDocs.map(doc => (
            <div key={doc.id} style={styles.docCard}>
              {editingDoc === doc.id ? (
                /* Edit mode */
                <div>
                  <select
                    style={{ ...styles.selectField, width: '100%', marginBottom: 6 }}
                    value={editCategory}
                    onChange={e => setEditCategory(e.target.value)}
                  >
                    {CATEGORIES.filter(c => c.value !== 'all').map(c => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                  <input
                    style={{ ...styles.inputField, marginBottom: 6 }}
                    value={editTags}
                    onChange={e => setEditTags(e.target.value)}
                    placeholder="Tags"
                  />
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button
                      style={{ ...styles.btn, ...styles.btnPrimary, ...styles.btnSmall }}
                      onClick={() => saveEdit(doc.id)}
                    >
                      Sauver
                    </button>
                    <button
                      style={{ ...styles.btn, ...styles.btnSecondary, ...styles.btnSmall }}
                      onClick={() => setEditingDoc(null)}
                    >
                      Annuler
                    </button>
                  </div>
                </div>
              ) : (
                /* Display mode */
                <>
                  <div style={styles.docCardHeader}>
                    <p style={styles.docFileName}>{doc.fileName}</p>
                    <span style={{ ...styles.docCategory, ...getCategoryStyle(doc.category) }}>
                      {CATEGORIES.find(c => c.value === doc.category)?.label || doc.category}
                    </span>
                  </div>
                  <div style={styles.docMeta}>
                    {new Date(doc.uploadedAt).toLocaleDateString('fr-FR')}
                    {doc.textLength ? ` · ${Math.round(doc.textLength / 1000)}k car.` : ''}
                    {doc.analyzed && ' · Analysé ✓'}
                    {doc.images && doc.images.length > 0 && (
                      <span style={{
                        marginLeft: 4,
                        padding: '1px 6px',
                        borderRadius: 4,
                        backgroundColor: '#e8f5e9',
                        color: '#2e7d32',
                        fontSize: 10,
                        fontWeight: 600,
                      }}>
                        {doc.images.length} image{doc.images.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                  {doc.tags.length > 0 && (
                    <div style={styles.docTags}>
                      {doc.tags.map((tag, i) => (
                        <span key={i} style={styles.docTag}>{tag}</span>
                      ))}
                    </div>
                  )}
                  <div style={styles.docActions}>
                    <button
                      style={{ ...styles.btn, ...styles.btnPrimary, ...styles.btnSmall }}
                      onClick={() => onAnalyze(doc.id)}
                      disabled={isLoading}
                    >
                      {doc.analyzed ? 'Re-analyser' : 'Analyser'}
                    </button>
                    <button
                      style={{ ...styles.btn, ...styles.btnSecondary, ...styles.btnSmall }}
                      onClick={() => startEdit(doc)}
                    >
                      Modifier
                    </button>
                    <button
                      style={{ ...styles.btn, ...styles.btnDanger, ...styles.btnSmall }}
                      onClick={() => onDelete(doc.id)}
                    >
                      Suppr.
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DocumentLibrary;
