import React, { useState } from 'react';
import styles from '../styles';

interface PseudonymEntry {
  id: string;
  placeholder: string;
  real: string;
  category: string;
}

interface Props {
  pseudonyms: PseudonymEntry[];
  onUpdate: (pseudonyms: PseudonymEntry[]) => void;
  onDetect: () => void;
  isLoading: boolean;
}

const CATEGORIES = [
  { value: 'company', label: 'Société' },
  { value: 'person', label: 'Personne' },
  { value: 'project', label: 'Projet' },
  { value: 'client', label: 'Client' },
  { value: 'reference', label: 'Référence' },
  { value: 'location', label: 'Lieu' },
  { value: 'financial', label: 'Financier' },
  { value: 'other', label: 'Autre' },
];

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  company: { bg: '#e3f2fd', text: '#1565c0' },
  person: { bg: '#f3e5f5', text: '#7b1fa2' },
  project: { bg: '#e8f5e9', text: '#2e7d32' },
  client: { bg: '#fff3e0', text: '#e65100' },
  reference: { bg: '#e0f7fa', text: '#00695c' },
  location: { bg: '#fce4ec', text: '#c62828' },
  financial: { bg: '#fff9c4', text: '#f57f17' },
  other: { bg: '#f5f5f5', text: '#616161' },
};

const PseudonymPanel: React.FC<Props> = ({ pseudonyms, onUpdate, onDetect, isLoading }) => {
  const [newPlaceholder, setNewPlaceholder] = useState('');
  const [newReal, setNewReal] = useState('');
  const [newCategory, setNewCategory] = useState('company');
  const [editId, setEditId] = useState<string | null>(null);
  const [editPlaceholder, setEditPlaceholder] = useState('');
  const [editReal, setEditReal] = useState('');
  const [editCategory, setEditCategory] = useState('');

  const addEntry = () => {
    if (!newPlaceholder.trim() || !newReal.trim()) return;
    const placeholder = newPlaceholder.trim().startsWith('[')
      ? newPlaceholder.trim()
      : `[${newPlaceholder.trim()}]`;
    const entry: PseudonymEntry = {
      id: `ps-${Date.now()}`,
      placeholder,
      real: newReal.trim(),
      category: newCategory,
    };
    onUpdate([...pseudonyms, entry]);
    setNewPlaceholder('');
    setNewReal('');
  };

  const deleteEntry = (id: string) => {
    onUpdate(pseudonyms.filter(p => p.id !== id));
  };

  const startEdit = (entry: PseudonymEntry) => {
    setEditId(entry.id);
    setEditPlaceholder(entry.placeholder);
    setEditReal(entry.real);
    setEditCategory(entry.category);
  };

  const saveEdit = () => {
    if (!editId) return;
    onUpdate(pseudonyms.map(p =>
      p.id === editId
        ? { ...p, placeholder: editPlaceholder, real: editReal, category: editCategory }
        : p
    ));
    setEditId(null);
  };

  return (
    <div style={{ padding: 20 }}>
      <h3 style={styles.sectionTitle}>Pseudonymisation</h3>
      <p style={styles.helpText}>
        Protégez les informations confidentielles en les remplaçant par des pseudonymes
        avant l'envoi à l'IA. Les vrais noms ne seront visibles que dans votre aperçu et vos exports.
      </p>

      {/* Auto-detect button */}
      <div style={{
        padding: 16,
        borderRadius: 8,
        backgroundColor: '#e8eaf6',
        border: '1px solid #9fa8da',
        marginBottom: 20,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
      }}>
        <div>
          <p style={{ fontSize: 13, fontWeight: 600, color: '#283593', margin: 0, marginBottom: 4 }}>
            Détection automatique
          </p>
          <p style={{ fontSize: 11, color: '#5c6bc0', margin: 0 }}>
            Analyse vos documents et détecte automatiquement les noms de sociétés, personnes, projets et autres données confidentielles.
          </p>
        </div>
        <button
          style={{
            ...styles.btn,
            backgroundColor: '#3949ab',
            color: '#fff',
            padding: '10px 20px',
            fontSize: 13,
            fontWeight: 600,
            whiteSpace: 'nowrap' as const,
            opacity: isLoading ? 0.5 : 1,
            cursor: isLoading ? 'not-allowed' : 'pointer',
          }}
          onClick={onDetect}
          disabled={isLoading}
        >
          {isLoading ? 'Détection en cours...' : 'Détecter automatiquement'}
        </button>
      </div>

      {/* Add form */}
      <div style={{
        padding: 14,
        border: '2px dashed var(--divider-color, #ddd)',
        borderRadius: 8,
        marginBottom: 20,
        display: 'flex',
        gap: 8,
        alignItems: 'flex-end',
        flexWrap: 'wrap' as const,
      }}>
        <div style={{ flex: 1, minWidth: 150 }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#888', display: 'block', marginBottom: 4 }}>
            Pseudonyme (ce que voit l'IA)
          </label>
          <input
            style={styles.inputField}
            placeholder="Ex: [Nom de la société]"
            value={newPlaceholder}
            onChange={e => setNewPlaceholder(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') addEntry(); }}
          />
        </div>
        <div style={{ flex: 1, minWidth: 150 }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#888', display: 'block', marginBottom: 4 }}>
            Valeur réelle (confidentielle)
          </label>
          <input
            style={styles.inputField}
            placeholder="Ex: SCC France"
            value={newReal}
            onChange={e => setNewReal(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') addEntry(); }}
          />
        </div>
        <div style={{ minWidth: 120 }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#888', display: 'block', marginBottom: 4 }}>
            Catégorie
          </label>
          <select
            style={styles.selectField}
            value={newCategory}
            onChange={e => setNewCategory(e.target.value)}
          >
            {CATEGORIES.map(c => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
        <button
          style={{ ...styles.btn, ...styles.btnPrimary }}
          onClick={addEntry}
          disabled={!newPlaceholder.trim() || !newReal.trim()}
        >
          Ajouter
        </button>
      </div>

      {/* Table */}
      {pseudonyms.length === 0 ? (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>🔒</div>
          <p style={styles.emptyText}>Aucune règle de pseudonymisation définie.</p>
          <p style={{ fontSize: 12, color: '#999' }}>
            Ajoutez des correspondances pour protéger les informations confidentielles.
          </p>
        </div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' as const, fontSize: 13 }}>
          <thead>
            <tr style={{ backgroundColor: 'var(--bg-color, #fafafa)' }}>
              <th style={thStyle}>Pseudonyme (vu par l'IA)</th>
              <th style={thStyle}>Valeur réelle</th>
              <th style={{ ...thStyle, width: 100 }}>Catégorie</th>
              <th style={{ ...thStyle, width: 80 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {pseudonyms.map(entry => (
              <tr key={entry.id} style={{ borderBottom: '1px solid var(--divider-color, #e0e0e0)' }}>
                {editId === entry.id ? (
                  <>
                    <td style={tdStyle}>
                      <input
                        style={{ ...styles.inputField, fontSize: 12, width: '100%' }}
                        value={editPlaceholder}
                        onChange={e => setEditPlaceholder(e.target.value)}
                      />
                    </td>
                    <td style={tdStyle}>
                      <input
                        style={{ ...styles.inputField, fontSize: 12, width: '100%' }}
                        value={editReal}
                        onChange={e => setEditReal(e.target.value)}
                      />
                    </td>
                    <td style={tdStyle}>
                      <select
                        style={{ ...styles.selectField, fontSize: 12, width: '100%' }}
                        value={editCategory}
                        onChange={e => setEditCategory(e.target.value)}
                      >
                        {CATEGORIES.map(c => (
                          <option key={c.value} value={c.value}>{c.label}</option>
                        ))}
                      </select>
                    </td>
                    <td style={tdStyle}>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button
                          style={{ ...styles.btn, ...styles.btnPrimary, ...styles.btnSmall }}
                          onClick={saveEdit}
                        >
                          OK
                        </button>
                        <button
                          style={{ ...styles.btn, ...styles.btnSecondary, ...styles.btnSmall }}
                          onClick={() => setEditId(null)}
                        >
                          X
                        </button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td style={tdStyle}>
                      <code style={{
                        backgroundColor: '#e3f2fd',
                        padding: '2px 6px',
                        borderRadius: 3,
                        fontSize: 12,
                        color: '#1565c0',
                      }}>
                        {entry.placeholder}
                      </code>
                    </td>
                    <td style={tdStyle}>
                      <span style={{ fontWeight: 500 }}>{entry.real}</span>
                    </td>
                    <td style={tdStyle}>
                      <span style={{
                        fontSize: 10,
                        fontWeight: 600,
                        padding: '2px 8px',
                        borderRadius: 4,
                        backgroundColor: (CATEGORY_COLORS[entry.category] || CATEGORY_COLORS.other).bg,
                        color: (CATEGORY_COLORS[entry.category] || CATEGORY_COLORS.other).text,
                      }}>
                        {CATEGORIES.find(c => c.value === entry.category)?.label || entry.category}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button
                          style={{ ...styles.btn, ...styles.btnSecondary, ...styles.btnSmall }}
                          onClick={() => startEdit(entry)}
                          title="Modifier"
                        >
                          &#9998;
                        </button>
                        <button
                          style={{ ...styles.btn, ...styles.btnDanger, ...styles.btnSmall }}
                          onClick={() => deleteEntry(entry.id)}
                          title="Supprimer"
                        >
                          &#x2715;
                        </button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {pseudonyms.length > 0 && (
        <div style={{
          marginTop: 16,
          padding: 12,
          borderRadius: 6,
          backgroundColor: '#e8f5e9',
          border: '1px solid #a5d6a7',
          fontSize: 12,
          color: '#2e7d32',
        }}>
          <strong>{pseudonyms.length} règle{pseudonyms.length > 1 ? 's' : ''} active{pseudonyms.length > 1 ? 's' : ''}</strong> —
          L'IA ne verra que les pseudonymes. Les valeurs réelles apparaissent uniquement dans vos aperçus et exports.
        </div>
      )}
    </div>
  );
};

const thStyle: React.CSSProperties = {
  padding: '8px 12px',
  textAlign: 'left',
  fontWeight: 600,
  fontSize: 11,
  color: '#888',
  borderBottom: '2px solid var(--divider-color, #e0e0e0)',
};

const tdStyle: React.CSSProperties = {
  padding: '8px 12px',
  verticalAlign: 'middle',
};

export default PseudonymPanel;
