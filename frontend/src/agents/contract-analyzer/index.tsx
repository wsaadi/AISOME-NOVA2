import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { AgentViewProps } from 'framework/types';
import { ChatPanel, FileUpload, ActionButton, DataTable, MarkdownView, SettingsPanel } from 'framework/components';
import { useAgent, useAgentStorage } from 'framework/hooks';
import styles from './styles';

const ContractAnalyzerView: React.FC<AgentViewProps> = ({ agent, sessionId, userId }) => {
  const { sendMessage, messages, isLoading, streamingContent, progress, progressMessage } = useAgent(agent.slug, sessionId);
  const storage = useAgentStorage(agent.slug);

  // State
  const [activeTab, setActiveTab] = useState<'analysis' | 'chat' | 'recommendations'>('analysis');
  const [currentAnalysis, setCurrentAnalysis] = useState<any>(null);
  const [riskTableData, setRiskTableData] = useState<Record<string, unknown>[]>([]);
  const [settings, setSettings] = useState({
    analysisMode: 'contract_only',
    autoAnalyze: true,
    includeComparison: false,
  });
  const [selectedTheme, setSelectedTheme] = useState<string>('');

  // Extract analysis data from messages
  useEffect(() => {
    const analysisMessages = messages.filter(m =>
      m.role === 'assistant' &&
      m.metadata?.type === 'contract_analysis'
    );

    if (analysisMessages.length > 0) {
      const latestAnalysis = analysisMessages[analysisMessages.length - 1];
      setCurrentAnalysis(latestAnalysis);

      // Parse risk table from content
      const content = latestAnalysis.content;
      const tableMatch = content.match(/\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|/g);
      if (tableMatch && tableMatch.length > 2) {
        const risks = tableMatch.slice(2).map((row: string, index: number) => {
          const cells = row.split('|').filter((cell: string) => cell.trim());
          return {
            id: index,
            risk: cells[0]?.trim() || '',
            category: cells[1]?.trim() || '',
            level: cells[2]?.trim() || '',
            impact: cells[3]?.trim() || '',
            recommendation: cells[4]?.trim() || '',
          };
        });
        setRiskTableData(risks);
      }
    }
  }, [messages]);

  // Handle file upload
  const handleFileUpload = useCallback(async (file: File) => {
    const key = await storage.upload(file);
    await sendMessage(
      `Analyser le contrat : ${file.name}`,
      {
        fileKey: key,
        fileName: file.name,
        settings: settings
      }
    );
    setActiveTab('analysis');
    return key;
  }, [sendMessage, storage, settings]);

  // Handle theme-specific questions
  const handleThemeQuestion = useCallback(async (theme: string) => {
    if (!currentAnalysis) return;

    const themeQuestions: Record<string, string> = {
      'penalties': 'Quelles sont toutes les p\u00e9nalit\u00e9s et indemnit\u00e9s pr\u00e9vues dans ce contrat ?',
      'termination': 'Quelles sont les conditions de r\u00e9siliation et leurs cons\u00e9quences ?',
      'liability': 'Quelle est l\'etendue des responsabilit\u00e9s et limitations ?',
      'ip': 'Qui d\u00e9tient la propri\u00e9t\u00e9 intellectuelle et sous quelles conditions ?',
      'data': 'Quelles sont les clauses relatives aux donn\u00e9es et \u00e0 la confidentialit\u00e9 ?',
      'sla': 'Quels sont les niveaux de service (SLA) garantis ?',
      'pricing': 'Quel est le mod\u00e8le de prix et les conditions de r\u00e9vision ?',
      'warranty': 'Quelles sont les garanties offertes et leurs limites ?',
    };

    const question = themeQuestions[theme];
    if (question) {
      await sendMessage(question, { settings });
      setActiveTab('chat');
    }
  }, [currentAnalysis, sendMessage, settings]);

  // Handle Word export
  const handleExportWord = useCallback(async () => {
    if (!currentAnalysis || !currentAnalysis.metadata?.wordReportKey) return;

    try {
      const blob = await storage.download(currentAnalysis.metadata.wordReportKey);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analyse_contrat_${new Date().toISOString().split('T')[0]}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export error:', error);
    }
  }, [currentAnalysis, storage]);

  // Risk level color coding
  const getRiskLevelColor = (level: string) => {
    const normalized = level.toLowerCase();
    if (normalized.includes('\u00e9lev\u00e9') || normalized.includes('high')) return '#d32f2f';
    if (normalized.includes('moyen') || normalized.includes('medium')) return '#f57c00';
    return '#388e3c';
  };

  // Render upload zone
  const renderUploadZone = () => (
    <div style={styles.uploadContainer}>
      <h2 style={styles.sectionTitle}>Analyser un nouveau contrat</h2>
      <FileUpload
        onUpload={handleFileUpload}
        accept=".pdf,.docx,.doc"
        label="D\u00e9posez votre contrat ici (PDF ou Word)"
        disabled={isLoading}
      />
      {progress > 0 && progress < 100 && (
        <div style={styles.progressContainer}>
          <div style={styles.progressBar}>
            <div style={{...styles.progressFill, width: `${progress}%`}} />
          </div>
          <p style={styles.progressText}>{progressMessage}</p>
        </div>
      )}
    </div>
  );

  // Render analysis tab
  const renderAnalysisTab = () => {
    if (!currentAnalysis) {
      return renderUploadZone();
    }

    return (
      <div style={styles.analysisContainer}>
        <div style={styles.analysisHeader}>
          <h2 style={styles.analysisTitle}>
            Analyse de : {currentAnalysis.metadata?.fileName}
          </h2>
          <div style={styles.analysisActions}>
            <ActionButton
              label="Exporter Word"
              onClick={handleExportWord}
              disabled={!currentAnalysis.metadata?.wordReportKey}
            />
            <ActionButton
              label="Nouvelle analyse"
              onClick={() => setCurrentAnalysis(null)}
            />
          </div>
        </div>

        <div style={styles.analysisContent}>
          <MarkdownView content={currentAnalysis.content} />
        </div>

        {riskTableData.length > 0 && (
          <div style={styles.riskTableContainer}>
            <h3 style={styles.sectionTitle}>Tableau des risques</h3>
            <DataTable
              columns={[
                { key: 'risk', label: 'Risque identifi\u00e9' },
                { key: 'category', label: 'Cat\u00e9gorie' },
                {
                  key: 'level',
                  label: 'Niveau',
                  render: (value) => (
                    <span style={{color: getRiskLevelColor(value as string), fontWeight: 'bold'}}>
                      {value}
                    </span>
                  )
                },
                { key: 'impact', label: 'Impact potentiel' },
                { key: 'recommendation', label: 'Recommandation' },
              ]}
              rows={riskTableData}
              emptyMessage="Aucun risque identifi\u00e9"
            />
          </div>
        )}
      </div>
    );
  };

  // Render recommendations tab
  const renderRecommendationsTab = () => {
    const themes = [
      { id: 'penalties', label: 'P\u00e9nalit\u00e9s et indemnit\u00e9s', icon: '\u26a0\ufe0f' },
      { id: 'termination', label: 'R\u00e9siliation', icon: '\ud83d\udea3' },
      { id: 'liability', label: 'Responsabilit\u00e9s', icon: '\u2696\ufe0f' },
      { id: 'ip', label: 'Propri\u00e9t\u00e9 intellectuelle', icon: '\u00a9\ufe0f' },
      { id: 'data', label: 'Donn\u00e9es et confidentialit\u00e9', icon: '\ud83d\udd12' },
      { id: 'sla', label: 'Niveaux de service', icon: '\ud83d\udcca' },
      { id: 'pricing', label: 'Prix et r\u00e9visions', icon: '\ud83d\udcb0' },
      { id: 'warranty', label: 'Garanties', icon: '\ud83d\udee1\ufe0f' },
    ];

    return (
      <div style={styles.recommendationsContainer}>
        <h2 style={styles.sectionTitle}>Analyses th\u00e9matiques</h2>
        <p style={styles.helpText}>
          Cliquez sur un th\u00e8me pour obtenir une analyse d\u00e9taill\u00e9e de cet aspect du contrat
        </p>

        <div style={styles.themeGrid}>
          {themes.map(theme => (
            <div
              key={theme.id}
              style={{
                ...styles.themeCard,
                ...(selectedTheme === theme.id ? styles.themeCardActive : {})
              }}
              onClick={() => {
                setSelectedTheme(theme.id);
                handleThemeQuestion(theme.id);
              }}
            >
              <span style={styles.themeIcon}>{theme.icon}</span>
              <span style={styles.themeLabel}>{theme.label}</span>
            </div>
          ))}
        </div>

        {!currentAnalysis && (
          <div style={styles.noAnalysisMessage}>
            <p>Veuillez d'abord analyser un contrat pour acc\u00e9der aux recommandations th\u00e9matiques</p>
          </div>
        )}
      </div>
    );
  };

  // Filter chat messages
  const chatMessages = useMemo(() => {
    return messages.filter(m => m.metadata?.type !== 'contract_analysis');
  }, [messages]);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.tabs}>
          <button
            style={{
              ...styles.tab,
              ...(activeTab === 'analysis' ? styles.tabActive : {})
            }}
            onClick={() => setActiveTab('analysis')}
          >
            Analyse
          </button>
          <button
            style={{
              ...styles.tab,
              ...(activeTab === 'chat' ? styles.tabActive : {})
            }}
            onClick={() => setActiveTab('chat')}
          >
            Questions
          </button>
          <button
            style={{
              ...styles.tab,
              ...(activeTab === 'recommendations' ? styles.tabActive : {})
            }}
            onClick={() => setActiveTab('recommendations')}
          >
            Th\u00e9matiques
          </button>
        </div>

        <div style={styles.settingsArea}>
          <SettingsPanel
            settings={[
              {
                key: 'analysisMode',
                label: 'Mode d\'analyse',
                type: 'select',
                options: [
                  { value: 'contract_only', label: 'Contrat seul' },
                  { value: 'best_practices', label: 'Avec bonnes pratiques' },
                  { value: 'comparison', label: 'Comparaison standards' },
                ]
              },
            ]}
            values={settings}
            onChange={(v) => setSettings(v as typeof settings)}
            title="Param\u00e8tres"
          />
        </div>
      </div>

      <div style={styles.content}>
        {activeTab === 'analysis' && renderAnalysisTab()}

        {activeTab === 'chat' && (
          <div style={styles.chatContainer}>
            {!currentAnalysis && (
              <div style={styles.chatHeader}>
                <p style={styles.helpText}>
                  Analysez d'abord un contrat pour pouvoir poser des questions sp\u00e9cifiques
                </p>
              </div>
            )}
            <ChatPanel
              messages={chatMessages}
              onSendMessage={(msg) => sendMessage(msg, { settings })}
              isLoading={isLoading}
              streamingContent={streamingContent}
              placeholder="Posez une question sur le contrat..."
              disabled={!currentAnalysis}
            />
          </div>
        )}

        {activeTab === 'recommendations' && renderRecommendationsTab()}
      </div>
    </div>
  );
};

export default ContractAnalyzerView;
