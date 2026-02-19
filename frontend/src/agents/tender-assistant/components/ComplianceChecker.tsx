import React, { useState, useMemo } from 'react';
import { MarkdownView, ActionButton } from 'framework/components';
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
  complianceResult: string | null;
  onRunCheck: () => void;
  isLoading: boolean;
}

const ComplianceChecker: React.FC<Props> = ({
  chapters, complianceResult, onRunCheck, isLoading,
}) => {
  const [showDetails, setShowDetails] = useState(true);

  // Compute basic stats from chapters
  const stats = useMemo(() => {
    let total = 0;
    let written = 0;
    let empty = 0;
    const countChapters = (chs: Chapter[]) => {
      for (const ch of chs) {
        total++;
        if (ch.content && ch.content.trim()) {
          written++;
        } else {
          empty++;
        }
        countChapters(ch.sub_chapters || []);
      }
    };
    countChapters(chapters);
    return { total, written, empty, coverage: total > 0 ? Math.round((written / total) * 100) : 0 };
  }, [chapters]);

  // Try to extract JSON compliance data from result
  const parsedResult = useMemo(() => {
    if (!complianceResult) return null;
    try {
      const start = complianceResult.indexOf('```json');
      if (start === -1) return null;
      const jsonStart = complianceResult.indexOf('{', start);
      const endMarker = complianceResult.indexOf('```', jsonStart);
      const jsonEnd = complianceResult.lastIndexOf('}', endMarker !== -1 ? endMarker : undefined) + 1;
      const data = JSON.parse(complianceResult.slice(jsonStart, jsonEnd));
      if (data.type === 'compliance_check') return data;
      return null;
    } catch {
      return null;
    }
  }, [complianceResult]);

  const getScoreColor = (score: number) => {
    if (score >= 80) return '#4caf50';
    if (score >= 60) return '#ff9800';
    return '#d32f2f';
  };

  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case 'critique': return { backgroundColor: '#ffebee', color: '#c62828' };
      case 'important': return { backgroundColor: '#fff3e0', color: '#e65100' };
      default: return { backgroundColor: '#f5f5f5', color: '#616161' };
    }
  };

  return (
    <div>
      {/* Action bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h3 style={styles.sectionTitle}>Vérification de conformité</h3>
          <p style={styles.helpText}>
            Vérifie que votre réponse couvre toutes les exigences de l'AO, est complète et cohérente.
          </p>
        </div>
        <ActionButton
          label={complianceResult ? 'Relancer la vérification' : 'Lancer la vérification'}
          onClick={onRunCheck}
          disabled={isLoading || chapters.length === 0}
        />
      </div>

      {/* Basic stats */}
      <div style={styles.statGrid}>
        <div style={styles.statCard}>
          <p style={{ ...styles.statValue, color: getScoreColor(stats.coverage) }}>
            {stats.coverage}%
          </p>
          <p style={styles.statLabel}>Couverture rédaction</p>
        </div>
        <div style={styles.statCard}>
          <p style={{ ...styles.statValue, color: '#333' }}>{stats.total}</p>
          <p style={styles.statLabel}>Sections totales</p>
        </div>
        <div style={styles.statCard}>
          <p style={{ ...styles.statValue, color: '#4caf50' }}>{stats.written}</p>
          <p style={styles.statLabel}>Sections rédigées</p>
        </div>
        <div style={styles.statCard}>
          <p style={{ ...styles.statValue, color: '#d32f2f' }}>{stats.empty}</p>
          <p style={styles.statLabel}>Sections vides</p>
        </div>
      </div>

      {/* Parsed compliance result */}
      {parsedResult && (
        <div style={{ marginBottom: 20 }}>
          <div style={styles.complianceScore}>
            <div style={{
              ...styles.scoreCircle,
              borderColor: getScoreColor(parsedResult.overall_score),
            }}>
              <span style={{ ...styles.scoreValue, color: getScoreColor(parsedResult.overall_score) }}>
                {parsedResult.overall_score}
              </span>
              <span style={styles.scoreLabel}>Score</span>
            </div>

            {parsedResult.requirements_coverage && (
              <div style={{ textAlign: 'left' as const }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Couverture des exigences</div>
                <div style={{ display: 'flex', gap: 16 }}>
                  <div>
                    <span style={{ fontSize: 18, fontWeight: 700, color: '#4caf50' }}>
                      {parsedResult.requirements_coverage.covered}
                    </span>
                    <span style={{ fontSize: 11, color: '#888' }}> couvertes</span>
                  </div>
                  <div>
                    <span style={{ fontSize: 18, fontWeight: 700, color: '#ff9800' }}>
                      {parsedResult.requirements_coverage.partial}
                    </span>
                    <span style={{ fontSize: 11, color: '#888' }}> partielles</span>
                  </div>
                  <div>
                    <span style={{ fontSize: 18, fontWeight: 700, color: '#d32f2f' }}>
                      {parsedResult.requirements_coverage.missing}
                    </span>
                    <span style={{ fontSize: 11, color: '#888' }}> manquantes</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Priority actions */}
          {parsedResult.priority_actions && parsedResult.priority_actions.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h4 style={styles.sectionTitle}>Actions prioritaires</h4>
              <div style={styles.issuesList}>
                {parsedResult.priority_actions.map((action: any, i: number) => (
                  <div key={i} style={styles.issueItem}>
                    <span style={{ ...styles.issueSeverity, ...getSeverityStyle(action.severity) }}>
                      {action.severity}
                    </span>
                    <div style={{ flex: 1 }}>
                      <p style={{ margin: 0, fontWeight: 500 }}>{action.action}</p>
                      {action.chapter && (
                        <p style={{ margin: '4px 0 0', color: '#888', fontSize: 11 }}>
                          Chapitre : {action.chapter}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Per-section status */}
          {parsedResult.sections && parsedResult.sections.length > 0 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <h4 style={styles.sectionTitle}>Détail par section</h4>
                <button
                  style={{ ...styles.btn, ...styles.btnSecondary, ...styles.btnSmall }}
                  onClick={() => setShowDetails(!showDetails)}
                >
                  {showDetails ? 'Masquer' : 'Afficher'}
                </button>
              </div>
              {showDetails && (
                <div style={styles.issuesList}>
                  {parsedResult.sections.map((section: any, i: number) => (
                    <div key={i} style={styles.issueItem}>
                      <div style={{
                        width: 40,
                        textAlign: 'center' as const,
                        fontWeight: 700,
                        color: getScoreColor(section.score),
                        fontSize: 16,
                      }}>
                        {section.score}
                      </div>
                      <div style={{ flex: 1 }}>
                        <p style={{ margin: 0, fontWeight: 600, fontSize: 13 }}>{section.title}</p>
                        <span style={{
                          fontSize: 10, fontWeight: 600, padding: '1px 6px', borderRadius: 3,
                          ...(section.status === 'complet'
                            ? { backgroundColor: '#e8f5e9', color: '#2e7d32' }
                            : section.status === 'partiel'
                            ? { backgroundColor: '#fff3e0', color: '#e65100' }
                            : { backgroundColor: '#ffebee', color: '#c62828' }),
                        }}>
                          {section.status}
                        </span>
                        {section.issues && section.issues.length > 0 && (
                          <ul style={{ margin: '6px 0 0', padding: '0 0 0 16px', fontSize: 11, color: '#666' }}>
                            {section.issues.map((issue: any, j: number) => (
                              <li key={j}>
                                <strong>{issue.type}</strong>: {issue.description}
                                {issue.suggestion && <em> → {issue.suggestion}</em>}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Full markdown result */}
      {complianceResult && (
        <div style={styles.analysisCard}>
          <div style={styles.analysisCardHeader}>
            <h4 style={styles.analysisCardTitle}>Rapport complet</h4>
          </div>
          <div style={styles.markdownContent}>
            <MarkdownView content={complianceResult} />
          </div>
        </div>
      )}

      {/* Empty state */}
      {!complianceResult && chapters.length > 0 && (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>✅</div>
          <p style={styles.emptyText}>
            Lancez la vérification pour obtenir un rapport de conformité détaillé.
          </p>
        </div>
      )}

      {chapters.length === 0 && (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>📋</div>
          <p style={styles.emptyText}>
            Générez d'abord la structure de réponse avant de vérifier la conformité.
          </p>
        </div>
      )}
    </div>
  );
};

export default ComplianceChecker;
