import React, { useState, useCallback } from 'react';
import styles, { PRIORITY_COLORS } from '../styles';

interface Improvement {
  id: string;
  title: string;
  description: string;
  priority: string;
  source: string;
  linkedChapters: string[];
  createdAt: string;
}

interface Chapter {
  id: string;
  number: string;
  title: string;
  sub_chapters: Chapter[];
}

interface Props {
  improvements: Improvement[];
  chapters: Chapter[];
  onAdd: (title: string, description: string, priority: string, linkedChapters: string[]) => void;
  onDelete: (id: string) => void;
  onBulkImport: (text: string) => void;
}

const ImprovementsPanel: React.FC<Props> = ({
  improvements, chapters, onAdd, onDelete, onBulkImport,
}) => {
  const [showForm, setShowForm] = useState(false);
  const [showBulkImport, setShowBulkImport] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('normal');
  const [linkedChapters, setLinkedChapters] = useState<string[]>([]);
  const [bulkText, setBulkText] = useState('');
  const [filterPriority, setFilterPriority] = useState('all');

  const handleAdd = useCallback(() => {
    if (!title.trim()) return;
    onAdd(title.trim(), description.trim(), priority, linkedChapters);
    setTitle('');
    setDescription('');
    setPriority('normal');
    setLinkedChapters([]);
    setShowForm(false);
  }, [title, description, priority, linkedChapters, onAdd]);

  const handleBulkImport = useCallback(() => {
    if (!bulkText.trim()) return;
    onBulkImport(bulkText.trim());
    setBulkText('');
    setShowBulkImport(false);
  }, [bulkText, onBulkImport]);

  const toggleChapter = (chapterId: string) => {
    setLinkedChapters(prev =>
      prev.includes(chapterId)
        ? prev.filter(id => id !== chapterId)
        : [...prev, chapterId]
    );
  };

  const getPriorityStyle = (p: string) => {
    const colors = PRIORITY_COLORS[p] || PRIORITY_COLORS.normal;
    return { backgroundColor: colors.bg, color: colors.text };
  };

  const filteredImprovements = filterPriority === 'all'
    ? improvements
    : improvements.filter(i => i.priority === filterPriority);

  const allChaptersList: { id: string; label: string }[] = [];
  for (const ch of chapters) {
    allChaptersList.push({ id: ch.id, label: `${ch.number} - ${ch.title}` });
    for (const sub of ch.sub_chapters || []) {
      allChaptersList.push({ id: sub.id, label: `  ${sub.number} - ${sub.title}` });
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h3 style={styles.sectionTitle}>Points d'amélioration ({improvements.length})</h3>
          <p style={styles.helpText}>
            Ajoutez les points d'amélioration connus (retours client, axes de progrès, engagements)
            pour les intégrer dans la rédaction.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            style={{ ...styles.btn, ...styles.btnPrimary }}
            onClick={() => { setShowForm(true); setShowBulkImport(false); }}
          >
            + Ajouter
          </button>
          <button
            style={{ ...styles.btn, ...styles.btnSecondary }}
            onClick={() => { setShowBulkImport(true); setShowForm(false); }}
          >
            Import texte
          </button>
        </div>
      </div>

      {/* Add form */}
      {showForm && (
        <div style={styles.addForm}>
          <div style={styles.formRow}>
            <input
              style={{ ...styles.inputField, fontWeight: 600 }}
              placeholder="Titre du point d'amélioration"
              value={title}
              onChange={e => setTitle(e.target.value)}
            />
            <select
              style={styles.selectField}
              value={priority}
              onChange={e => setPriority(e.target.value)}
            >
              <option value="critique">Critique</option>
              <option value="haute">Haute</option>
              <option value="normal">Normale</option>
              <option value="basse">Basse</option>
            </select>
          </div>
          <textarea
            style={{ ...styles.inputField, minHeight: 60, resize: 'vertical' as const }}
            placeholder="Description détaillée..."
            value={description}
            onChange={e => setDescription(e.target.value)}
          />

          {/* Link to chapters */}
          {allChaptersList.length > 0 && (
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#888', display: 'block', marginBottom: 4 }}>
                Lier à des chapitres :
              </label>
              <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: 4, maxHeight: 120, overflow: 'auto' }}>
                {allChaptersList.map(ch => (
                  <button
                    key={ch.id}
                    style={{
                      ...styles.filterChip,
                      ...(linkedChapters.includes(ch.id) ? styles.filterChipActive : {}),
                      fontSize: 10,
                      padding: '2px 8px',
                    }}
                    onClick={() => toggleChapter(ch.id)}
                  >
                    {ch.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 6 }}>
            <button
              style={{ ...styles.btn, ...styles.btnPrimary, ...((!title.trim()) ? styles.btnDisabled : {}) }}
              onClick={handleAdd}
              disabled={!title.trim()}
            >
              Ajouter
            </button>
            <button
              style={{ ...styles.btn, ...styles.btnSecondary }}
              onClick={() => setShowForm(false)}
            >
              Annuler
            </button>
          </div>
        </div>
      )}

      {/* Bulk import */}
      {showBulkImport && (
        <div style={styles.addForm}>
          <p style={{ fontSize: 12, color: '#666', margin: '0 0 8px' }}>
            Collez ou tapez vos points d'amélioration en texte libre. L'IA les analysera et les structurera automatiquement.
          </p>
          <textarea
            style={{ ...styles.inputField, minHeight: 120, resize: 'vertical' as const }}
            placeholder="Ex: Améliorer le temps de réponse du support N1 à 2h au lieu de 4h. Proposer une solution de monitoring proactive. Renforcer l'équipe avec un expert sécurité dédié..."
            value={bulkText}
            onChange={e => setBulkText(e.target.value)}
          />
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              style={{ ...styles.btn, ...styles.btnPrimary, ...((!bulkText.trim()) ? styles.btnDisabled : {}) }}
              onClick={handleBulkImport}
              disabled={!bulkText.trim()}
            >
              Importer et analyser
            </button>
            <button
              style={{ ...styles.btn, ...styles.btnSecondary }}
              onClick={() => setShowBulkImport(false)}
            >
              Annuler
            </button>
          </div>
        </div>
      )}

      {/* Filter */}
      {improvements.length > 0 && (
        <div style={{ ...styles.filterBar, marginBottom: 12 }}>
          {['all', 'critique', 'haute', 'normal', 'basse'].map(p => (
            <button
              key={p}
              style={{
                ...styles.filterChip,
                ...(filterPriority === p ? styles.filterChipActive : {}),
              }}
              onClick={() => setFilterPriority(p)}
            >
              {p === 'all' ? 'Tous' : p.charAt(0).toUpperCase() + p.slice(1)}
              {p !== 'all' && ` (${improvements.filter(i => i.priority === p).length})`}
            </button>
          ))}
        </div>
      )}

      {/* Improvements list */}
      {filteredImprovements.length === 0 && improvements.length === 0 ? (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>💡</div>
          <p style={styles.emptyText}>
            Aucun point d'amélioration enregistré.
          </p>
          <p style={{ fontSize: 12, color: '#aaa' }}>
            Ajoutez les retours client, axes de progrès et engagements connus depuis le marché précédent.
          </p>
        </div>
      ) : (
        filteredImprovements.map(imp => (
          <div key={imp.id} style={styles.improvementCard}>
            <div style={styles.improvementHeader}>
              <p style={styles.improvementTitle}>{imp.title}</p>
              <span style={{ ...styles.priorityBadge, ...getPriorityStyle(imp.priority) }}>
                {imp.priority}
              </span>
              <button
                style={{ ...styles.btn, ...styles.btnDanger, ...styles.btnSmall, padding: '2px 6px' }}
                onClick={() => onDelete(imp.id)}
                title="Supprimer"
              >
                ×
              </button>
            </div>
            {imp.description && (
              <p style={styles.improvementDesc}>{imp.description}</p>
            )}
            {imp.linkedChapters && imp.linkedChapters.length > 0 && (
              <div style={{ marginTop: 6, display: 'flex', gap: 4, flexWrap: 'wrap' as const }}>
                {imp.linkedChapters.map(chId => {
                  const ch = allChaptersList.find(c => c.id === chId);
                  return ch ? (
                    <span key={chId} style={{ ...styles.docTag, fontSize: 9 }}>{ch.label}</span>
                  ) : null;
                })}
              </div>
            )}
            <div style={{ fontSize: 10, color: '#bbb', marginTop: 6 }}>
              {imp.source === 'manual' ? 'Ajout manuel' : imp.source} · {new Date(imp.createdAt).toLocaleDateString('fr-FR')}
            </div>
          </div>
        ))
      )}
    </div>
  );
};

export default ImprovementsPanel;
