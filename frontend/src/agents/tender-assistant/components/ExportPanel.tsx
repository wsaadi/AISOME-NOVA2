import React, { useState, useCallback } from 'react';
import { FileUpload, ActionButton } from 'framework/components';
import styles from '../styles';

interface Chapter {
  id: string;
  number: string;
  title: string;
  content: string;
  status: string;
  sub_chapters: Chapter[];
}

interface Props {
  chapters: Chapter[];
  templateKey: string | null;
  templateName: string | null;
  onExport: (title: string, templateKey: string | null) => void;
  onUploadTemplate: (file: File) => Promise<void>;
  onDownloadFile: (fileKey: string, fileName: string) => void;
  lastExportKey: string | null;
  lastExportName: string | null;
  isLoading: boolean;
  progress: number;
  progressMessage: string;
}

const ExportPanel: React.FC<Props> = ({
  chapters, templateKey, templateName, onExport, onUploadTemplate,
  onDownloadFile, lastExportKey, lastExportName, isLoading, progress, progressMessage,
}) => {
  const [title, setTitle] = useState("Réponse à l'Appel d'Offres");

  // Count chapter stats
  const stats = (() => {
    let total = 0;
    let written = 0;
    let totalPages = 0;
    const count = (chs: Chapter[]) => {
      for (const ch of chs) {
        total++;
        if (ch.content) written++;
        totalPages += (ch as any).estimated_pages || 0;
        count(ch.sub_chapters || []);
      }
    };
    count(chapters);
    return { total, written, totalPages };
  })();

  const handleUpload = useCallback(async (file: File) => {
    await onUploadTemplate(file);
    return '';
  }, [onUploadTemplate]);

  return (
    <div style={styles.exportContainer}>
      <h3 style={styles.sectionTitle}>Export de la réponse</h3>
      <p style={styles.helpText}>
        Exportez votre réponse complète en format Word (.docx) professionnel.
      </p>

      {/* Stats summary */}
      <div style={styles.statGrid}>
        <div style={styles.statCard}>
          <p style={{ ...styles.statValue, color: '#333' }}>{stats.total}</p>
          <p style={styles.statLabel}>Sections</p>
        </div>
        <div style={styles.statCard}>
          <p style={{ ...styles.statValue, color: '#4caf50' }}>{stats.written}</p>
          <p style={styles.statLabel}>Rédigées</p>
        </div>
        <div style={styles.statCard}>
          <p style={{ ...styles.statValue, color: '#d32f2f' }}>{stats.total - stats.written}</p>
          <p style={styles.statLabel}>Manquantes</p>
        </div>
        <div style={styles.statCard}>
          <p style={{ ...styles.statValue, color: '#1976d2' }}>~{stats.totalPages}</p>
          <p style={styles.statLabel}>Pages est.</p>
        </div>
      </div>

      {/* Title */}
      <div style={styles.exportSection}>
        <label style={styles.exportLabel}>Titre du document</label>
        <input
          style={styles.exportInput}
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Titre du document exporté"
        />
      </div>

      {/* Template */}
      <div style={styles.exportSection}>
        <label style={styles.exportLabel}>Template Word (charte graphique)</label>
        {templateKey ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: '#4caf50', fontWeight: 600 }}>
              ✓ Template chargé : {templateName}
            </span>
          </div>
        ) : (
          <p style={{ fontSize: 12, color: '#888', marginBottom: 8 }}>
            Uploadez votre template Word pour que l'export respecte votre charte graphique.
          </p>
        )}
        <FileUpload
          onUpload={handleUpload}
          accept=".docx"
          label="Déposez votre template DOCX ici"
          disabled={isLoading}
        />
      </div>

      {/* Warning if incomplete */}
      {stats.written < stats.total && (
        <div style={{
          padding: 12,
          borderRadius: 6,
          backgroundColor: '#fff3e0',
          border: '1px solid #ffcc02',
          marginBottom: 16,
          fontSize: 12,
          color: '#e65100',
        }}>
          <strong>Attention :</strong> {stats.total - stats.written} section(s) n'ont pas encore de contenu.
          Les sections vides apparaîtront avec leur description dans le document exporté.
        </div>
      )}

      {/* Export button */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <ActionButton
          label="Exporter en DOCX"
          onClick={() => onExport(title, templateKey)}
          disabled={isLoading || chapters.length === 0}
        />

        {lastExportKey && lastExportName && (
          <button
            style={{ ...styles.btn, ...styles.btnSecondary }}
            onClick={() => onDownloadFile(lastExportKey, lastExportName)}
          >
            Télécharger le dernier export
          </button>
        )}
      </div>

      {/* Progress */}
      {progress > 0 && progress < 100 && (
        <div style={{ marginTop: 12 }}>
          <div style={styles.progressBar}>
            <div style={{ ...styles.progressFill, width: `${progress}%` }} />
          </div>
          <p style={styles.progressText}>{progressMessage}</p>
        </div>
      )}

      {/* Chapter preview */}
      <div style={{ marginTop: 24 }}>
        <h4 style={styles.sectionTitle}>Aperçu de la structure</h4>
        <div style={{
          padding: 12,
          borderRadius: 6,
          border: '1px solid var(--divider-color, #e0e0e0)',
          fontSize: 12,
          lineHeight: 1.8,
          maxHeight: 300,
          overflow: 'auto' as const,
        }}>
          {chapters.map(ch => (
            <div key={ch.id}>
              <div style={{ fontWeight: 600 }}>
                {ch.content ? '✓' : '○'} {ch.number}. {ch.title}
              </div>
              {(ch.sub_chapters || []).map(sub => (
                <div key={sub.id} style={{ paddingLeft: 20, color: '#666' }}>
                  {sub.content ? '✓' : '○'} {sub.number}. {sub.title}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ExportPanel;
