import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
import WorkspaceSelector from './components/WorkspaceSelector';

// =============================================================================
// Types
// =============================================================================

type ViewId = 'documents' | 'analysis' | 'editor' | 'compliance' | 'export' | 'improvements';

interface NavItem {
  id: ViewId;
  label: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'documents', label: 'Documents', icon: '📁' },
  { id: 'analysis', label: 'Analyse', icon: '🔍' },
  { id: 'editor', label: 'Rédaction', icon: '✏️' },
  { id: 'compliance', label: 'Conformité', icon: '✅' },
  { id: 'improvements', label: 'Améliorations', icon: '💡' },
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
    progress, progressMessage,
  } = useAgent(agent.slug, sessionId, { workspaceId });
  const storage = useAgentStorage(agent.slug, { workspaceId });

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
  const [stateLoaded, setStateLoaded] = useState(false);

  // -- Load initial state --
  useEffect(() => {
    if (!stateLoaded) {
      sendMessage('', { action: 'get_project_state' }).then(() => {
        setStateLoaded(true);
      });
    }
  }, []);

  // -- Process messages to update state --
  useEffect(() => {
    for (const msg of messages) {
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
          break;

        case 'template_uploaded':
          setTemplateKey(meta.templateKey);
          setTemplateName(meta.fileName);
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

  // -- Export handlers --
  const handleExport = useCallback((title: string, tplKey: string | null) => {
    sendMessage('', { action: 'export_docx', title, templateKey: tplKey });
  }, [sendMessage]);

  const handleUploadTemplate = useCallback(async (file: File) => {
    const key = await storage.upload(file);
    await sendMessage('', { action: 'upload_template', fileKey: key, fileName: file.name });
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

  return (
    <div style={styles.root}>
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
              color: '#1976d2',
              background: 'none',
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
              {chatOpen ? '◀ Masquer le chat' : '▶ Ouvrir le chat'}
            </button>
          </div>
        </div>

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
              onSaveContent={handleSaveContent}
              onUpdateStructure={handleUpdateStructure}
              isLoading={isLoading}
              streamingContent={streamingContent}
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

          {activeView === 'export' && (
            <ExportPanel
              chapters={chapters}
              templateKey={templateKey}
              templateName={templateName}
              onExport={handleExport}
              onUploadTemplate={handleUploadTemplate}
              onDownloadFile={handleDownloadFile}
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
