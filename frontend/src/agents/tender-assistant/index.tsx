import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useTheme } from '@mui/material/styles';
import { AgentViewProps } from 'framework/types';
import { ChatPanel } from 'framework/components';
import { useAgent, useAgentStorage } from 'framework/hooks';
import styles from './styles';

import DocumentLibrary from './components/DocumentLibrary';
import AnalysisView from './components/AnalysisView';
import ResponseEditor from './components/ResponseEditor';
import ComplianceChecker from './components/ComplianceChecker';
import ExportPanel from './components/ExportPanel';
import ImprovementsPanel from './components/ImprovementsPanel';
import PseudonymPanel from './components/PseudonymPanel';
import WorkspaceSelector from './components/WorkspaceSelector';

// =============================================================================
// Types
// =============================================================================

type ViewId = 'documents' | 'analysis' | 'editor' | 'compliance' | 'export' | 'improvements' | 'confidentiality' | 'statistics';

interface NavItem {
  id: ViewId;
  label: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'documents', label: 'Documents', icon: '📁' },
  { id: 'analysis', label: 'Analyse', icon: '🔍' },
  { id: 'editor', label: 'Rédaction', icon: '✏️' },
  { id: 'statistics', label: 'Tableau de bord', icon: '📊' },
  { id: 'compliance', label: 'Conformité', icon: '✅' },
  { id: 'improvements', label: 'Améliorations', icon: '💡' },
  { id: 'confidentiality', label: 'Confidentialité', icon: '🔒' },
  { id: 'export', label: 'Export', icon: '📤' },
];

// =============================================================================
// Workspace gate — shown before the main agent view
// =============================================================================

const TenderAssistantGate: React.FC<AgentViewProps> = (props) => {
  const storageKey = `workspace_${props.agent.slug}`;
  const [workspaceId, setWorkspaceId] = useState<string | null>(() =>
    localStorage.getItem(storageKey)
  );

  const handleSelect = (id: string) => {
    localStorage.setItem(storageKey, id);
    setWorkspaceId(id);
  };

  const handleChangeWorkspace = () => {
    localStorage.removeItem(storageKey);
    setWorkspaceId(null);
  };

  if (!workspaceId) {
    return <WorkspaceSelector agentSlug={props.agent.slug} onSelect={handleSelect} />;
  }

  return (
    <TenderAssistantView
      {...props}
      workspaceId={workspaceId}
      onChangeWorkspace={handleChangeWorkspace}
    />
  );
};

// =============================================================================
// Main Component
// =============================================================================

interface TenderAssistantInternalProps extends AgentViewProps {
  workspaceId: string;
  onChangeWorkspace: () => void;
}

const TenderAssistantView: React.FC<TenderAssistantInternalProps> = ({
  agent, sessionId, workspaceId, onChangeWorkspace,
}) => {
  const {
    sendMessage, messages, isLoading, streamingContent,
    progress, progressMessage, sessionRestored, error,
  } = useAgent(agent.slug, sessionId, { workspaceId });
  const storage = useAgentStorage(agent.slug, { workspaceId });
  const muiTheme = useTheme();
  const isDark = muiTheme.palette.mode === 'dark';

  // Dark-mode CSS variable overrides (applied on the root div)
  const darkVars: React.CSSProperties = isDark ? {
    '--ta-bg': '#0F172A',
    '--ta-bg-alt': '#1E293B',
    '--ta-surface': '#1a2236',
    '--ta-text': '#F1F5F9',
    '--ta-text-dim': '#94A3B8',
    '--ta-border': '#334155',
    '--ta-primary': '#818CF8',
    '--ta-primary-bg': 'rgba(129,140,248,0.10)',
  } as React.CSSProperties : {};

  // -- State --
  const [activeView, setActiveView] = useState<ViewId>('documents');
  const [chatOpen, setChatOpen] = useState(true);
  const [documents, setDocuments] = useState<any[]>([]);
  const [chapters, setChapters] = useState<any[]>([]);
  const [improvements, setImprovements] = useState<any[]>([]);
  const [analyses, setAnalyses] = useState<Record<string, any>>({});
  const [complianceResult, setComplianceResult] = useState<string | null>(null);
  const [templateKey, setTemplateKey] = useState<string | null>(null);
  const [templateName, setTemplateName] = useState<string | null>(null);
  const [lastExportKey, setLastExportKey] = useState<string | null>(null);
  const [lastExportName, setLastExportName] = useState<string | null>(null);
  const [pseudonyms, setPseudonyms] = useState<any[]>([]);
  const [stateLoaded, setStateLoaded] = useState(false);
  const processedMsgCount = useRef(0);

  // -- Load initial state (wait for session restore first) --
  useEffect(() => {
    if (sessionRestored && !stateLoaded) {
      // Skip restored messages — get_project_state will give us fresh state.
      // Without this, the messages effect would re-process old messages
      // (e.g. all_documents_analyzed) and trigger sendMessage loops.
      processedMsgCount.current = messages.length;
      sendMessage('', { action: 'get_project_state' }).then(() => {
        setStateLoaded(true);
      });
    }
  }, [sessionRestored]);

  // -- Process NEW messages only to update state --
  // We track how many messages we've already processed to avoid
  // re-processing old messages (which would cause infinite loops
  // when a handler calls sendMessage).
  useEffect(() => {
    const startIdx = processedMsgCount.current;
    if (messages.length <= startIdx) return;
    processedMsgCount.current = messages.length;

    const newMessages = messages.slice(startIdx);

    for (const msg of newMessages) {
      if (msg.role !== 'assistant' || !msg.metadata) continue;
      const meta = msg.metadata as Record<string, any>;
      const { type } = meta;

      switch (type) {
        case 'project_state':
          if (meta.state) {
            setDocuments(meta.state.documents || []);
            setChapters(meta.state.chapters || []);
            setImprovements(meta.state.improvements || []);
            setAnalyses(meta.state.analyses || {});
            setPseudonyms(meta.state.pseudonyms || []);
          }
          break;

        case 'document_uploaded':
          if (meta.document) {
            setDocuments(prev => {
              const exists = prev.some((d: any) => d.id === meta.document.id);
              return exists ? prev : [...prev, meta.document];
            });
          }
          break;

        case 'document_deleted':
          setDocuments(prev => prev.filter((d: any) => d.id !== meta.documentId));
          break;

        case 'document_updated':
          // Reload state
          break;

        case 'document_analysis':
          setAnalyses(prev => ({
            ...prev,
            [meta.documentId]: {
              fileName: meta.fileName,
              content: msg.content,
              analyzedAt: new Date().toISOString(),
            },
          }));
          setDocuments(prev => prev.map((d: any) =>
            d.id === meta.documentId ? { ...d, analyzed: true } : d
          ));
          break;

        case 'all_documents_analyzed':
          if (meta.analyzedDocIds) {
            setDocuments(prev => prev.map((d: any) =>
              meta.analyzedDocIds.includes(d.id) ? { ...d, analyzed: true } : d
            ));
          }
          // Reload full state to get all analyses content
          sendMessage('', { action: 'get_project_state' });
          break;

        case 'comparison_result':
          setAnalyses(prev => ({
            ...prev,
            _comparison: {
              content: msg.content,
              comparedAt: new Date().toISOString(),
            },
          }));
          break;

        case 'structure_generated':
          if (meta.chapters && meta.chapters.length > 0) {
            setChapters(meta.chapters);
          }
          break;

        case 'structure_updated':
          if (meta.chapters) {
            setChapters(meta.chapters);
          }
          break;

        case 'chapter_written':
        case 'chapter_improved':
          // Update chapter content from the message
          if (meta.chapterId) {
            setChapters(prev => updateChapterContent(prev, meta.chapterId, msg.content));
          }
          break;

        case 'write_all_complete':
        case 'improve_all_complete':
          if (meta.chapters) {
            setChapters(meta.chapters);
          }
          break;

        case 'compliance_check':
          setComplianceResult(msg.content);
          break;

        case 'improvement_added':
          if (meta.improvement) {
            setImprovements(prev => {
              const exists = prev.some((i: any) => i.id === meta.improvement.id);
              return exists ? prev : [...prev, meta.improvement];
            });
          }
          break;

        case 'improvement_deleted':
          setImprovements(prev => prev.filter((i: any) => i.id !== meta.improvementId));
          break;

        case 'export_complete':
          setLastExportKey(meta.fileKey);
          setLastExportName(meta.fileName);
          // Auto-trigger DOCX download
          if (meta.fileKey && meta.fileName) {
            storage.download(meta.fileKey).then(blob => {
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = meta.fileName;
              a.click();
              URL.revokeObjectURL(url);
            }).catch(err => console.error('Auto-download export failed:', err));
          }
          break;

        case 'template_uploaded':
          setTemplateKey(meta.templateKey);
          setTemplateName(meta.fileName);
          break;

        case 'pseudonyms_updated':
          if (meta.pseudonyms) {
            setPseudonyms(meta.pseudonyms);
          }
          // Retroactive pseudonymization may have updated chapters
          if (meta.chapters) {
            setChapters(meta.chapters);
          }
          break;

        case 'confidential_detected':
          if (meta.pseudonyms) {
            setPseudonyms(meta.pseudonyms);
          }
          break;

        case 'pseudonyms_applied':
          if (meta.chapters) {
            setChapters(meta.chapters);
          }
          break;

        case 'formatting_cleaned':
          if (meta.chapters) {
            setChapters(meta.chapters);
          }
          break;

        case 'workspace_exported':
          if (meta.fileKey && meta.fileName) {
            setLastExportKey(meta.fileKey);
            setLastExportName(meta.fileName);
            // Auto-trigger download
            storage.download(meta.fileKey).then(blob => {
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = meta.fileName;
              a.click();
              URL.revokeObjectURL(url);
            }).catch(err => console.error('Auto-download workspace export failed:', err));
          }
          break;

        case 'workspace_imported':
          // Full state refresh
          if (meta.state) {
            setDocuments(meta.state.documents || []);
            setChapters(meta.state.chapters || []);
            setImprovements(meta.state.improvements || []);
            setAnalyses(meta.state.analyses || {});
            setPseudonyms(meta.state.pseudonyms || []);
          }
          break;
      }
    }
  }, [messages]);

  // -- Document handlers --
  const handleUploadDocument = useCallback(async (file: File, category: string, tags: string[]) => {
    const key = await storage.upload(file);
    await sendMessage(`Document uploadé : ${file.name}`, {
      action: 'upload_document',
      fileKey: key,
      fileName: file.name,
      category,
      tags,
    });
  }, [storage, sendMessage]);

  const handleDeleteDocument = useCallback((docId: string) => {
    sendMessage('', { action: 'delete_document', documentId: docId });
  }, [sendMessage]);

  const handleAnalyzeDocument = useCallback((docId: string) => {
    sendMessage('', { action: 'analyze_document', documentId: docId });
  }, [sendMessage]);

  const handleUpdateDocumentMeta = useCallback((docId: string, category: string, tags: string[]) => {
    sendMessage('', { action: 'update_document_meta', documentId: docId, category, tags });
  }, [sendMessage]);

  const handleAnalyzeAll = useCallback(() => {
    sendMessage('Analyse tous les documents non analysés', { action: 'analyze_all_documents' });
  }, [sendMessage]);

  // -- Analysis handlers --
  const handleCompare = useCallback(() => {
    sendMessage('Compare les anciens et nouveaux documents AO', { action: 'compare_tenders' });
  }, [sendMessage]);

  // -- Structure handlers --
  const handleGenerateStructure = useCallback(() => {
    sendMessage('Génère la structure de réponse', { action: 'generate_structure' });
  }, [sendMessage]);

  const handleUpdateStructure = useCallback((updatedChapters: any[]) => {
    sendMessage('', { action: 'update_structure', chapters: updatedChapters });
  }, [sendMessage]);

  // -- Writing handlers --
  const handleWriteChapter = useCallback((chapterId: string, instructions: string) => {
    sendMessage(instructions || '', { action: 'write_chapter', chapterId });
  }, [sendMessage]);

  const handleImproveChapter = useCallback((chapterId: string, instructions: string) => {
    sendMessage(instructions, { action: 'improve_chapter', chapterId });
  }, [sendMessage]);

  const handleWriteAll = useCallback(() => {
    sendMessage('Rédige tous les chapitres non rédigés', { action: 'write_all_chapters' });
  }, [sendMessage]);

  const handleImproveAll = useCallback(() => {
    sendMessage('Améliore tous les chapitres rédigés', { action: 'improve_all_chapters' });
  }, [sendMessage]);

  const handleSaveContent = useCallback((chapterId: string, content: string) => {
    // Update locally immediately
    setChapters(prev => updateChapterContent(prev, chapterId, content));
    // Persist via update_structure
    const updated = updateChapterContent(chapters, chapterId, content);
    sendMessage('', { action: 'update_structure', chapters: updated });
  }, [chapters, sendMessage]);

  // -- Compliance handler --
  const handleCheckCompliance = useCallback(() => {
    sendMessage('Vérifie la conformité de la réponse', { action: 'check_compliance' });
  }, [sendMessage]);

  // -- Improvement handlers --
  const handleAddImprovement = useCallback((title: string, description: string, priority: string, linkedChapters: string[]) => {
    sendMessage(description, { action: 'add_improvement', title, description, priority, linkedChapters });
  }, [sendMessage]);

  const handleDeleteImprovement = useCallback((id: string) => {
    sendMessage('', { action: 'delete_improvement', improvementId: id });
  }, [sendMessage]);

  const handleBulkImport = useCallback((text: string) => {
    // Send as chat message asking AI to parse and add improvements
    sendMessage(
      `Analyse le texte suivant et identifie les points d'amélioration. Pour chaque point identifié, donne un titre, une description, et une priorité (critique/haute/normal/basse) :\n\n${text}`,
      { action: 'chat' }
    );
  }, [sendMessage]);

  // -- Pseudonym handlers --
  const handleUpdatePseudonyms = useCallback((updated: any[]) => {
    setPseudonyms(updated);
    sendMessage('', { action: 'update_pseudonyms', pseudonyms: updated });
  }, [sendMessage]);

  const handleApplyPseudonyms = useCallback(() => {
    sendMessage('', { action: 'apply_pseudonyms' });
  }, [sendMessage]);

  const handleCleanupFormatting = useCallback(() => {
    sendMessage('', { action: 'cleanup_formatting' });
  }, [sendMessage]);

  const handleDetectConfidential = useCallback(() => {
    sendMessage('Détecte les données confidentielles dans les documents', { action: 'detect_confidential' });
  }, [sendMessage]);

  // -- Export handlers --
  const handleExport = useCallback((title: string, tplKey: string | null) => {
    sendMessage('', { action: 'export_docx', title, templateKey: tplKey });
  }, [sendMessage]);

  const handleUploadTemplate = useCallback(async (file: File) => {
    const key = await storage.upload(file);
    await sendMessage('', { action: 'upload_template', fileKey: key, fileName: file.name });
  }, [storage, sendMessage]);

  // -- Workspace export/import handlers --
  const handleExportWorkspace = useCallback(() => {
    sendMessage('', { action: 'export_workspace' });
  }, [sendMessage]);

  const handleImportWorkspace = useCallback(async (file: File) => {
    const key = await storage.upload(file);
    await sendMessage('', { action: 'import_workspace', fileKey: key });
  }, [storage, sendMessage]);

  const handleDownloadFile = useCallback(async (fileKey: string, fileName: string) => {
    try {
      const blob = await storage.download(fileKey);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download error:', error);
    }
  }, [storage]);

  // -- Chat messages (filter out action responses for cleaner chat) --
  const chatMessages = useMemo(() => {
    return messages.filter(m =>
      m.metadata?.type === 'chat_response' ||
      m.role === 'user' && !m.metadata?.action
    );
  }, [messages]);

  // -- Badge counts --
  const getBadgeCount = (viewId: ViewId): number | null => {
    switch (viewId) {
      case 'documents': return documents.length || null;
      case 'analysis': return Object.keys(analyses).length || null;
      case 'editor': return chapters.length || null;
      case 'improvements': return improvements.length || null;
      default: return null;
    }
  };

  // ==========================================================================
  // Render
  // ==========================================================================

  // Show a loading screen while the workspace state is being fetched
  if (!stateLoaded) {
    return (
      <div style={{
        ...styles.root,
        ...darkVars,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column' as const,
        gap: 16,
      }}>
        <div style={{
          width: 48,
          height: 48,
          border: `4px solid var(--ta-border, #e0e0e0)`,
          borderTopColor: 'var(--ta-primary, #1976d2)',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }} />
        <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--ta-text, #555)' }}>
          Chargement de l'espace de travail...
        </p>
        <p style={{ fontSize: 12, color: 'var(--ta-text-dim, #999)' }}>
          Récupération des documents, chapitres et analyses
        </p>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div className="ta-root" style={{ ...styles.root, ...darkVars }}>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        .ta-resize-handle { background: transparent; transition: background 0.15s; }
        .ta-resize-handle:hover { background: var(--ta-primary, #1976d2); }
        .ta-root button {
          -webkit-appearance: none !important;
          -moz-appearance: none !important;
          appearance: none !important;
          outline: none !important;
          background: transparent;
          border: none;
          font-family: inherit;
          color: inherit;
        }
        .ta-root button:focus,
        .ta-root button:focus-visible,
        .ta-root button:active {
          outline: none !important;
        }
      `}</style>

      {/* Left Sidebar */}
      <div style={styles.sidebar}>
        <div style={styles.sidebarHeader}>
          <h2 style={styles.sidebarTitle}>Assistant AO</h2>
          <p style={styles.sidebarSubtitle}>Réponse à l'appel d'offres</p>
        </div>

        <div style={styles.navList}>
          {NAV_ITEMS.map(item => {
            const badge = getBadgeCount(item.id);
            return (
              <button
                key={item.id}
                style={{
                  ...styles.navItem,
                  ...(activeView === item.id ? styles.navItemActive : {}),
                }}
                onClick={() => setActiveView(item.id)}
              >
                <span style={styles.navIcon}>{item.icon}</span>
                <span style={styles.navLabel}>{item.label}</span>
                {badge !== null && <span style={styles.navBadge}>{badge}</span>}
              </button>
            );
          })}
        </div>

        <div style={styles.sidebarFooter}>
          <div>{documents.length} docs · {chapters.length} chapitres</div>
          <button
            onClick={onChangeWorkspace}
            style={{
              marginTop: 6,
              fontSize: 10,
              color: 'var(--ta-primary, #1976d2)',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: 0,
              textDecoration: 'underline',
            }}
          >
            Changer d'espace de travail
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div style={styles.main}>
        <div style={styles.mainHeader}>
          <h2 style={styles.mainTitle}>
            {NAV_ITEMS.find(n => n.id === activeView)?.icon}{' '}
            {NAV_ITEMS.find(n => n.id === activeView)?.label}
          </h2>
          <div style={styles.mainActions}>
            {activeView === 'analysis' && chapters.length === 0 && (
              <button
                style={{ ...styles.btn, ...styles.btnPrimary, ...(isLoading ? styles.btnDisabled : {}) }}
                onClick={handleGenerateStructure}
                disabled={isLoading}
              >
                Générer la structure
              </button>
            )}
            <button
              style={styles.chatToggle}
              onClick={() => setChatOpen(!chatOpen)}
            >
              {chatOpen ? 'Masquer le chat' : 'Ouvrir le chat'}
            </button>
          </div>
        </div>

        {/* Global progress banner */}
        {isLoading && progress > 0 && (
          <div style={{
            padding: '10px 20px',
            backgroundColor: 'var(--ta-primary-bg, #e3f2fd)',
            borderBottom: '1px solid var(--ta-border, #90caf9)',
            flexShrink: 0,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ta-primary, #1565c0)' }}>
                {progressMessage || 'Traitement en cours...'}
              </span>
              <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--ta-primary, #1565c0)' }}>
                {progress}%
              </span>
            </div>
            <div style={{
              height: 6,
              borderRadius: 3,
              backgroundColor: 'var(--ta-bg-alt, #bbdefb)',
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%',
                borderRadius: 3,
                backgroundColor: 'var(--ta-primary, #1976d2)',
                width: `${progress}%`,
                transition: 'width 0.4s ease',
              }} />
            </div>
          </div>
        )}
        {isLoading && progress === 0 && (
          <div style={{
            padding: '8px 20px',
            backgroundColor: 'var(--ta-bg-alt, #fff8e1)',
            borderBottom: '1px solid var(--ta-border, #ffe082)',
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            <span style={{
              display: 'inline-block',
              width: 14,
              height: 14,
              border: '2px solid var(--ta-primary, #f9a825)',
              borderTopColor: 'transparent',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
            }} />
            <span style={{ fontSize: 13, color: 'var(--ta-text-dim, #f57f17)' }}>
              {progressMessage || 'Chargement en cours...'}
            </span>
          </div>
        )}

        <div style={activeView === 'editor' ? { ...styles.mainContent, padding: 0, display: 'flex', flex: 1, overflow: 'hidden' } : styles.mainContent}>
          {activeView === 'documents' && (
            <DocumentLibrary
              documents={documents}
              onUpload={handleUploadDocument}
              onDelete={handleDeleteDocument}
              onAnalyze={handleAnalyzeDocument}
              onUpdateMeta={handleUpdateDocumentMeta}
              isLoading={isLoading}
              progress={progress}
              progressMessage={progressMessage}
            />
          )}

          {activeView === 'analysis' && (
            <AnalysisView
              analyses={analyses}
              documents={documents}
              onAnalyzeDocument={handleAnalyzeDocument}
              onAnalyzeAll={handleAnalyzeAll}
              onCompare={handleCompare}
              isLoading={isLoading}
              comparisonAvailable={Object.keys(analyses).includes('_comparison')}
            />
          )}

          {activeView === 'editor' && (
            <ResponseEditor
              chapters={chapters}
              onWriteChapter={handleWriteChapter}
              onImproveChapter={handleImproveChapter}
              onWriteAll={handleWriteAll}
              onImproveAll={handleImproveAll}
              onSaveContent={handleSaveContent}
              onUpdateStructure={handleUpdateStructure}
              onGenerateStructure={handleGenerateStructure}
              onCleanupFormatting={handleCleanupFormatting}
              isLoading={isLoading}
              streamingContent={streamingContent}
              error={error}
              pseudonyms={pseudonyms}
            />
          )}

          {activeView === 'statistics' && (
            <StatisticsPanel
              chapters={chapters}
              documents={documents}
              analyses={analyses}
              pseudonyms={pseudonyms}
              improvements={improvements}
              complianceResult={complianceResult}
            />
          )}

          {activeView === 'compliance' && (
            <ComplianceChecker
              chapters={chapters}
              complianceResult={complianceResult}
              onRunCheck={handleCheckCompliance}
              isLoading={isLoading}
            />
          )}

          {activeView === 'improvements' && (
            <ImprovementsPanel
              improvements={improvements}
              chapters={chapters}
              onAdd={handleAddImprovement}
              onDelete={handleDeleteImprovement}
              onBulkImport={handleBulkImport}
            />
          )}

          {activeView === 'confidentiality' && (
            <PseudonymPanel
              pseudonyms={pseudonyms}
              onUpdate={handleUpdatePseudonyms}
              onDetect={handleDetectConfidential}
              onApplyAll={handleApplyPseudonyms}
              isLoading={isLoading}
            />
          )}

          {activeView === 'export' && (
            <ExportPanel
              chapters={chapters}
              templateKey={templateKey}
              templateName={templateName}
              onExport={handleExport}
              onUploadTemplate={handleUploadTemplate}
              onDownloadFile={handleDownloadFile}
              onExportWorkspace={handleExportWorkspace}
              onImportWorkspace={handleImportWorkspace}
              lastExportKey={lastExportKey}
              lastExportName={lastExportName}
              isLoading={isLoading}
              progress={progress}
              progressMessage={progressMessage}
            />
          )}
        </div>
      </div>

      {/* Right Chat Panel */}
      <div style={chatOpen ? styles.chatPanel : styles.chatPanelCollapsed}>
        {chatOpen && (
          <>
            <div style={styles.chatHeader}>
              <h3 style={styles.chatTitle}>Assistant IA</h3>
              <button
                style={{
                  ...styles.btn,
                  ...styles.btnSmall,
                  ...styles.btnSecondary,
                }}
                onClick={() => setChatOpen(false)}
              >
                Fermer
              </button>
            </div>
            <ChatPanel
              messages={chatMessages}
              onSendMessage={(msg) => sendMessage(msg, { action: 'chat' })}
              isLoading={isLoading}
              streamingContent={streamingContent}
              placeholder="Posez une question sur l'AO, demandez une analyse..."
            />
          </>
        )}
      </div>
    </div>
  );
};

// =============================================================================
// Statistics Panel
// =============================================================================

interface StatisticsPanelProps {
  chapters: any[];
  documents: any[];
  analyses: Record<string, any>;
  pseudonyms: any[];
  improvements: any[];
  complianceResult: any;
}

const StatisticsPanel: React.FC<StatisticsPanelProps> = ({
  chapters, documents, analyses, pseudonyms, improvements, complianceResult,
}) => {
  // Compute stats
  let totalChapters = 0;
  let writtenChapters = 0;
  let totalWords = 0;
  const count = (chs: any[]) => {
    for (const ch of chs) {
      totalChapters++;
      if (ch.content) {
        writtenChapters++;
        totalWords += ch.content.split(/\s+/).filter(Boolean).length;
      }
      count(ch.sub_chapters || []);
    }
  };
  count(chapters);

  const redactionProgress = totalChapters > 0 ? Math.round((writtenChapters / totalChapters) * 100) : 0;
  const pageEstimate = Math.ceil(totalWords / 300);
  const analyzedDocs = Object.keys(analyses).filter(k => k !== '_comparison').length;
  const pseudonymCount = pseudonyms.length;
  const pseudonymsFilled = pseudonyms.filter((p: any) => p.real && p.placeholder).length;
  const complianceScore = complianceResult?.score ?? null;
  const improvementCount = improvements.length;

  const StatCard = ({ label, value, color, sub }: { label: string; value: string | number; color: string; sub?: string }) => (
    <div style={{
      padding: 20,
      borderRadius: 10,
      border: `1px solid var(--ta-border, #e2e5e9)`,
      backgroundColor: 'var(--ta-bg, #fff)',
      textAlign: 'center' as const,
    }}>
      <div style={{ fontSize: 32, fontWeight: 700, color, marginBottom: 4 }}>{value}</div>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--ta-text, #333)' }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--ta-text-dim, #888)', marginTop: 2 }}>{sub}</div>}
    </div>
  );

  const ProgressRow = ({ label, percent, color }: { label: string; percent: number; color: string }) => (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ta-text, #333)' }}>{label}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color }}>{percent}%</span>
      </div>
      <div style={{ height: 8, borderRadius: 4, backgroundColor: 'var(--ta-bg-alt, #f0f0f0)', overflow: 'hidden' }}>
        <div style={{ height: '100%', borderRadius: 4, backgroundColor: color, width: `${percent}%`, transition: 'width 0.4s ease' }} />
      </div>
    </div>
  );

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ta-text, #333)', margin: '0 0 20px' }}>
        Tableau de bord
      </h3>

      {/* Key metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12, marginBottom: 24 }}>
        <StatCard label="Chapitres rédigés" value={`${writtenChapters}/${totalChapters}`} color="#4caf50" sub={`${redactionProgress}% complet`} />
        <StatCard label="Mots rédigés" value={totalWords.toLocaleString()} color="#1976d2" sub={`~${pageEstimate} pages`} />
        <StatCard label="Documents" value={documents.length} color="#ff9800" sub={`${analyzedDocs} analysé(s)`} />
        <StatCard label="Données masquées" value={pseudonymsFilled} color="#7b1fa2" sub={`${pseudonymCount} règle(s)`} />
      </div>

      {/* Progress bars */}
      <div style={{
        padding: 20,
        borderRadius: 10,
        border: `1px solid var(--ta-border, #e2e5e9)`,
        backgroundColor: 'var(--ta-bg, #fff)',
        marginBottom: 24,
      }}>
        <h4 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 16px', color: 'var(--ta-text, #333)' }}>Progression</h4>
        <ProgressRow label="Rédaction" percent={redactionProgress} color="#4caf50" />
        <ProgressRow label="Analyse documentaire" percent={documents.length > 0 ? Math.round((analyzedDocs / documents.length) * 100) : 0} color="#ff9800" />
        {complianceScore !== null && (
          <ProgressRow label="Conformité AO" percent={complianceScore} color={complianceScore >= 80 ? '#4caf50' : complianceScore >= 60 ? '#ff9800' : '#d32f2f'} />
        )}
        <ProgressRow label="Pseudonymisation" percent={pseudonymCount > 0 ? Math.round((pseudonymsFilled / pseudonymCount) * 100) : 0} color="#7b1fa2" />
      </div>

      {/* Suggestions */}
      <div style={{
        padding: 20,
        borderRadius: 10,
        border: `1px solid var(--ta-border, #e2e5e9)`,
        backgroundColor: 'var(--ta-bg, #fff)',
        marginBottom: 24,
      }}>
        <h4 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px', color: 'var(--ta-text, #333)' }}>Suggestions d'amélioration</h4>
        <div style={{ display: 'flex', flexDirection: 'column' as const, gap: 8 }}>
          {totalChapters - writtenChapters > 0 && (
            <SuggestionItem
              icon="✏️"
              text={`${totalChapters - writtenChapters} chapitre(s) restent à rédiger`}
              priority="haute"
            />
          )}
          {documents.length - analyzedDocs > 0 && (
            <SuggestionItem
              icon="🔍"
              text={`${documents.length - analyzedDocs} document(s) n'ont pas encore été analysés`}
              priority="normal"
            />
          )}
          {complianceScore === null && writtenChapters > 0 && (
            <SuggestionItem
              icon="✅"
              text="Lancez une vérification de conformité pour évaluer votre réponse"
              priority="normal"
            />
          )}
          {complianceScore !== null && complianceScore < 80 && (
            <SuggestionItem
              icon="⚠️"
              text={`Score de conformité à ${complianceScore}% — des améliorations sont recommandées`}
              priority="haute"
            />
          )}
          {pseudonymCount === 0 && (
            <SuggestionItem
              icon="🔒"
              text="Configurez la pseudonymisation pour protéger les données confidentielles"
              priority="normal"
            />
          )}
          {pseudonymCount > 0 && pseudonymsFilled < pseudonymCount && (
            <SuggestionItem
              icon="🔒"
              text={`${pseudonymCount - pseudonymsFilled} pseudonyme(s) n'ont pas de valeur réelle renseignée`}
              priority="basse"
            />
          )}
          {improvementCount > 0 && (
            <SuggestionItem
              icon="💡"
              text={`${improvementCount} point(s) d'amélioration identifiés à intégrer`}
              priority="normal"
            />
          )}
          {writtenChapters === totalChapters && totalChapters > 0 && complianceScore !== null && complianceScore >= 80 && (
            <SuggestionItem
              icon="🎉"
              text="Votre réponse est complète et conforme. Prête pour l'export !"
              priority="ok"
            />
          )}
        </div>
      </div>
    </div>
  );
};

const SUGGESTION_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  haute: { bg: '#fff3e0', text: '#e65100', border: '#ffcc02' },
  normal: { bg: '#e3f2fd', text: '#1565c0', border: '#90caf9' },
  basse: { bg: '#f5f5f5', text: '#616161', border: '#e0e0e0' },
  ok: { bg: '#e8f5e9', text: '#2e7d32', border: '#a5d6a7' },
};

const SuggestionItem: React.FC<{ icon: string; text: string; priority: string }> = ({ icon, text, priority }) => {
  const c = SUGGESTION_COLORS[priority] || SUGGESTION_COLORS.normal;
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '10px 14px',
      borderRadius: 6,
      backgroundColor: c.bg,
      border: `1px solid ${c.border}`,
      fontSize: 13,
      color: c.text,
    }}>
      <span style={{ fontSize: 16 }}>{icon}</span>
      <span>{text}</span>
    </div>
  );
};

// =============================================================================
// Helpers
// =============================================================================

function updateChapterContent(chapters: any[], chapterId: string, content: string): any[] {
  return chapters.map(ch => {
    if (ch.id === chapterId) {
      return { ...ch, content, status: 'written', lastModified: new Date().toISOString() };
    }
    if (ch.sub_chapters) {
      return {
        ...ch,
        sub_chapters: ch.sub_chapters.map((sub: any) =>
          sub.id === chapterId
            ? { ...sub, content, status: 'written', lastModified: new Date().toISOString() }
            : sub
        ),
      };
    }
    return ch;
  });
}

export default TenderAssistantGate;
