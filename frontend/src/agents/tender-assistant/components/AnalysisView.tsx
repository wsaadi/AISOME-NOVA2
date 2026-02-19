import React, { useState } from 'react';
import { MarkdownView, ActionButton } from 'framework/components';
import styles from '../styles';

interface AnalysisData {
  documentId?: string;
  fileName?: string;
  category?: string;
  content: string;
  analyzedAt: string;
  comparedAt?: string;
  oldDocs?: string[];
  newDocs?: string[];
}

interface Props {
  analyses: Record<string, AnalysisData>;
  documents: Array<{ id: string; fileName: string; category: string; analyzed: boolean }>;
  onAnalyzeDocument: (docId: string) => void;
  onCompare: () => void;
  isLoading: boolean;
  comparisonAvailable: boolean;
}

const AnalysisView: React.FC<Props> = ({
  analyses, documents, onAnalyzeDocument, onCompare, isLoading, comparisonAvailable,
}) => {
  const [selectedAnalysis, setSelectedAnalysis] = useState<string | null>(null);

  const comparison = analyses['_comparison'];
  const docAnalyses = Object.entries(analyses).filter(([k]) => !k.startsWith('_'));

  const oldAoDocs = documents.filter(d => d.category === 'ancien_ao');
  const newAoDocs = documents.filter(d => d.category === 'nouvel_ao');
  const prevResponseDocs = documents.filter(d => d.category === 'ancienne_reponse');

  const analyzedCount = documents.filter(d => d.analyzed).length;

  return (
    <div style={styles.analysisLayout}>
      {/* Stats */}
      <div style={styles.statGrid}>
        <div style={styles.statCard}>
          <p style={{ ...styles.statValue, color: '#e65100' }}>{oldAoDocs.length}</p>
          <p style={styles.statLabel}>Docs ancien AO</p>
        </div>
        <div style={styles.statCard}>
          <p style={{ ...styles.statValue, color: '#1565c0' }}>{newAoDocs.length}</p>
          <p style={styles.statLabel}>Docs nouvel AO</p>
        </div>
        <div style={styles.statCard}>
          <p style={{ ...styles.statValue, color: '#7b1fa2' }}>{prevResponseDocs.length}</p>
          <p style={styles.statLabel}>Ancienne réponse</p>
        </div>
        <div style={styles.statCard}>
          <p style={{ ...styles.statValue, color: '#2e7d32' }}>{analyzedCount}</p>
          <p style={styles.statLabel}>Docs analysés</p>
        </div>
      </div>

      {/* Comparison banner */}
      <div style={styles.comparisonBanner}>
        <div style={{ flex: 1 }}>
          <strong style={{ fontSize: 14 }}>Comparaison Ancien AO ↔ Nouvel AO</strong>
          <p style={{ fontSize: 12, margin: '4px 0 0', color: '#555' }}>
            {comparison
              ? `Dernière comparaison : ${new Date(comparison.analyzedAt || comparison.comparedAt || '').toLocaleDateString('fr-FR')}`
              : 'Lancez la comparaison pour identifier les écarts entre les deux appels d\'offres.'}
          </p>
        </div>
        <ActionButton
          label={comparison ? 'Relancer' : 'Comparer'}
          onClick={onCompare}
          disabled={isLoading || oldAoDocs.length === 0 || newAoDocs.length === 0}
        />
      </div>

      {/* Comparison result */}
      {comparison && !selectedAnalysis && (
        <div style={styles.analysisCard}>
          <div style={styles.analysisCardHeader}>
            <h3 style={styles.analysisCardTitle}>Résultat de la comparaison</h3>
            <span style={{ fontSize: 11, color: '#888' }}>
              {comparison.oldDocs?.join(', ')} vs {comparison.newDocs?.join(', ')}
            </span>
          </div>
          <div style={styles.markdownContent}>
            <MarkdownView content={comparison.content} />
          </div>
        </div>
      )}

      {/* Selected analysis detail */}
      {selectedAnalysis && analyses[selectedAnalysis] && (
        <div style={styles.analysisCard}>
          <div style={styles.analysisCardHeader}>
            <h3 style={styles.analysisCardTitle}>
              Analyse : {analyses[selectedAnalysis].fileName}
            </h3>
            <button
              style={{ ...styles.btn, ...styles.btnSecondary, ...styles.btnSmall }}
              onClick={() => setSelectedAnalysis(null)}
            >
              Retour
            </button>
          </div>
          <div style={styles.markdownContent}>
            <MarkdownView content={analyses[selectedAnalysis].content} />
          </div>
        </div>
      )}

      {/* List of document analyses */}
      {!selectedAnalysis && (
        <>
          <h3 style={styles.sectionTitle}>Analyses de documents ({docAnalyses.length})</h3>
          {docAnalyses.length === 0 ? (
            <div style={styles.emptyState}>
              <p style={styles.emptyText}>
                Aucune analyse réalisée. Sélectionnez un document dans la bibliothèque et lancez l'analyse.
              </p>
            </div>
          ) : (
            docAnalyses.map(([key, analysis]) => (
              <div
                key={key}
                style={{ ...styles.analysisCard, cursor: 'pointer' }}
                onClick={() => setSelectedAnalysis(key)}
              >
                <div style={styles.analysisCardHeader}>
                  <h4 style={styles.analysisCardTitle}>{analysis.fileName}</h4>
                  <span style={{ fontSize: 11, color: '#888' }}>
                    {new Date(analysis.analyzedAt).toLocaleDateString('fr-FR')}
                  </span>
                </div>
                <p style={{ fontSize: 12, color: '#666', margin: '4px 0 0' }}>
                  {analysis.content.slice(0, 200)}...
                </p>
              </div>
            ))
          )}

          {/* Quick analyze buttons for unanalyzed docs */}
          {documents.filter(d => !d.analyzed).length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h3 style={styles.sectionTitle}>Documents non analysés</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: 8 }}>
                {documents.filter(d => !d.analyzed).map(doc => (
                  <button
                    key={doc.id}
                    style={{ ...styles.btn, ...styles.btnPrimary, ...styles.btnSmall }}
                    onClick={() => onAnalyzeDocument(doc.id)}
                    disabled={isLoading}
                  >
                    Analyser : {doc.fileName}
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AnalysisView;
