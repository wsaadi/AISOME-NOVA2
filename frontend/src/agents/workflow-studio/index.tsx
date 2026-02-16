/**
 * Workflow Studio — Create, import, and publish N8N workflow automations.
 *
 * Three tabs:
 *  1. Design (Chat) — Conversational workflow creation via AI
 *  2. Import — Import existing N8N workflow JSON files
 *  3. N8N Editor — Embedded N8N visual editor (iframe)
 *
 * When a workflow is generated or imported:
 *  - Analysis panel shows detected inputs, steps, and UI mode
 *  - Publish button creates a NOVA2 agent from the workflow
 */

import React, { useState, useMemo, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { AgentViewProps, ChatMessage } from 'framework/types';
import { ChatPanel, ActionButton } from 'framework/components';
import { useAgent } from 'framework/hooks';
import styles from './styles';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface WorkflowAnalysis {
  trigger_type: string;
  inputs: Array<{
    name: string;
    type: string;
    label: string;
    description: string;
    required: boolean;
    options?: string[];
  }>;
  steps: Array<{
    order: number;
    name: string;
    category: string;
    description: string;
    requires_human: boolean;
  }>;
  has_human_validation: boolean;
  has_file_upload: boolean;
  has_ai: boolean;
  has_chat: boolean;
  node_count: number;
  ui_mode: string;
  output_type: string;
}

interface PublishConfig {
  name: string;
  slug: string;
  description: string;
  icon: string;
}

interface GeneratedWorkflow {
  workflow_json: Record<string, unknown>;
  publish_config: PublishConfig | null;
  analysis: WorkflowAnalysis;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const extractGenerated = (messages: ChatMessage[]): GeneratedWorkflow | null => {
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (
      msg.role === 'assistant' &&
      msg.metadata?.phase === 'generated' &&
      msg.metadata?.workflow_json
    ) {
      return {
        workflow_json: msg.metadata.workflow_json as Record<string, unknown>,
        publish_config: (msg.metadata.publish_config as PublishConfig) || null,
        analysis: msg.metadata.analysis as WorkflowAnalysis,
      };
    }
  }
  return null;
};

const UI_MODE_LABELS: Record<string, string> = {
  form: 'Form',
  chat: 'Chat',
  pipeline: 'Pipeline',
  simple: 'Simple',
};

const CATEGORY_COLORS: Record<string, string> = {
  ai: '#7c3aed',
  processing: '#2563eb',
  output: '#059669',
  validation: '#d97706',
  input: '#6366f1',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const WorkflowStudioView: React.FC<AgentViewProps> = ({ agent, sessionId }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'design' | 'import' | 'editor'>('design');
  const [publishStatus, setPublishStatus] = useState<'idle' | 'publishing' | 'success' | 'error'>('idle');
  const [publishMessage, setPublishMessage] = useState('');
  const [importJson, setImportJson] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    sendMessage,
    messages,
    isLoading,
    streamingContent,
    progress,
    progressMessage,
    error,
  } = useAgent(agent.slug, sessionId);

  // Extract generated workflow from conversation
  const generated = useMemo(() => extractGenerated(messages), [messages]);

  // --- Import handler ---
  const handleFileImport = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    try {
      JSON.parse(text); // Validate JSON
      // Send the JSON as a message to the agent (it detects imports)
      sendMessage(text);
      setActiveTab('design');
    } catch {
      setPublishMessage(t('workflowStudio.invalidJson', 'Invalid JSON file'));
    }
  }, [sendMessage, t]);

  const handlePasteImport = useCallback(() => {
    if (!importJson.trim()) return;
    try {
      JSON.parse(importJson); // Validate
      sendMessage(importJson);
      setImportJson('');
      setActiveTab('design');
    } catch {
      setPublishMessage(t('workflowStudio.invalidJson', 'Invalid JSON'));
    }
  }, [importJson, sendMessage, t]);

  // --- Publish handler ---
  const handlePublish = useCallback(async () => {
    if (!generated) return;
    setPublishStatus('publishing');
    setPublishMessage('');

    const config = generated.publish_config || {
      name: 'Workflow Agent',
      slug: 'workflow-agent',
      description: '',
      icon: 'account_tree',
    };

    try {
      const token = localStorage.getItem('access_token');
      const API_BASE = process.env.REACT_APP_API_URL || '';

      // First, create the workflow in N8N
      const createResp = await fetch(`${API_BASE}/api/n8n/workflows`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ workflow_json: generated.workflow_json }),
      });

      let n8nWorkflowId: string;
      if (createResp.ok) {
        const createData = await createResp.json();
        n8nWorkflowId = String(createData.workflow?.id || '');
      } else {
        throw new Error('Failed to create workflow in N8N');
      }

      // Then publish as a NOVA2 agent
      const publishResp = await fetch(`${API_BASE}/api/n8n/workflows/${n8nWorkflowId}/publish`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: config.name,
          slug: config.slug,
          description: config.description,
          icon: config.icon,
        }),
      });

      if (!publishResp.ok) {
        const errData = await publishResp.json().catch(() => ({ detail: publishResp.statusText }));
        throw new Error(errData.detail || `Publish failed (${publishResp.status})`);
      }

      const data = await publishResp.json();
      setPublishStatus('success');
      setPublishMessage(
        t('workflowStudio.publishSuccess', 'Agent "{{name}}" published! Open it from the catalog.').replace('{{name}}', data.name)
      );
    } catch (err) {
      setPublishStatus('error');
      setPublishMessage(err instanceof Error ? err.message : 'Publish failed');
    }
  }, [generated, t]);

  // --- Download JSON handler ---
  const handleDownloadJson = useCallback(() => {
    if (!generated) return;
    const blob = new Blob(
      [JSON.stringify(generated.workflow_json, null, 2)],
      { type: 'application/json' },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${generated.publish_config?.slug || 'workflow'}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [generated]);

  const n8nUrl = process.env.REACT_APP_N8N_URL || 'http://localhost:5678';

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.headerIcon} className="material-icons">account_tree</span>
          <div>
            <h3 style={styles.headerTitle}>{t('workflowStudio.title', 'Workflow Studio')}</h3>
            <p style={styles.headerSubtitle}>{t('workflowStudio.subtitle', 'Create N8N automations as platform agents')}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={styles.tabBar}>
        <div
          style={activeTab === 'design' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('design')}
        >
          {t('workflowStudio.tabDesign', 'Design with AI')}
        </div>
        <div
          style={activeTab === 'import' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('import')}
        >
          {t('workflowStudio.tabImport', 'Import JSON')}
        </div>
        <div
          style={activeTab === 'editor' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('editor')}
        >
          {t('workflowStudio.tabEditor', 'N8N Editor')}
        </div>
      </div>

      {/* Progress bar */}
      {isLoading && progress > 0 && (
        <div style={styles.progressBar}>
          <div style={styles.progressTrack}>
            <div style={{ ...styles.progressFill, width: `${progress}%` }} />
          </div>
          <span style={styles.progressText}>{progressMessage || `${progress}%`}</span>
        </div>
      )}

      {/* Error */}
      {error && <div style={styles.errorBanner}>{error}</div>}

      {/* Results panel — shown when a workflow is generated */}
      {generated && (
        <div style={styles.resultsPanel}>
          <div style={styles.resultHeader}>
            <h4 style={styles.resultTitle}>
              {generated.publish_config?.name || t('workflowStudio.workflowReady', 'Workflow Ready')}
            </h4>
            <span style={styles.resultBadge}>
              {generated.analysis.node_count} nodes
            </span>
          </div>

          {/* Analysis cards */}
          <div style={styles.analysisGrid}>
            <div style={styles.analysisCard}>
              <div style={styles.analysisLabel}>{t('workflowStudio.triggerType', 'Trigger')}</div>
              <div style={styles.analysisValue}>{generated.analysis.trigger_type}</div>
            </div>
            <div style={styles.analysisCard}>
              <div style={styles.analysisLabel}>{t('workflowStudio.uiMode', 'UI Mode')}</div>
              <div style={styles.analysisValue}>{UI_MODE_LABELS[generated.analysis.ui_mode] || generated.analysis.ui_mode}</div>
            </div>
            <div style={styles.analysisCard}>
              <div style={styles.analysisLabel}>{t('workflowStudio.outputType', 'Output')}</div>
              <div style={styles.analysisValue}>{generated.analysis.output_type}</div>
            </div>
            <div style={styles.analysisCard}>
              <div style={styles.analysisLabel}>{t('workflowStudio.features', 'Features')}</div>
              <div style={styles.analysisValue}>
                {[
                  generated.analysis.has_ai && 'AI',
                  generated.analysis.has_chat && 'Chat',
                  generated.analysis.has_file_upload && 'Files',
                  generated.analysis.has_human_validation && 'Approval',
                ].filter(Boolean).join(', ') || 'Standard'}
              </div>
            </div>
          </div>

          {/* Inputs detected */}
          {generated.analysis.inputs.length > 0 && (
            <div style={styles.inputsSection}>
              <div style={styles.stepsTitle}>{t('workflowStudio.requiredInputs', 'Required Inputs')}</div>
              {generated.analysis.inputs.map((input, i) => (
                <div key={i} style={styles.inputItem}>
                  <span style={styles.inputType}>{input.type}</span>
                  <span>{input.label}</span>
                  {input.required && <span style={styles.inputRequired}>*</span>}
                </div>
              ))}
            </div>
          )}

          {/* Steps */}
          {generated.analysis.steps.length > 0 && (
            <div style={styles.stepsSection}>
              <div style={styles.stepsTitle}>{t('workflowStudio.workflowSteps', 'Workflow Steps')}</div>
              <div style={styles.stepsList}>
                {generated.analysis.steps.map((step) => (
                  <div key={step.order} style={styles.stepItem}>
                    <div style={styles.stepOrder}>{step.order}</div>
                    <span style={styles.stepName}>{step.name}</span>
                    <span style={{
                      ...styles.stepCategory,
                      backgroundColor: CATEGORY_COLORS[step.category]
                        ? `${CATEGORY_COLORS[step.category]}15`
                        : styles.stepCategory.backgroundColor,
                      color: CATEGORY_COLORS[step.category] || styles.stepCategory.color,
                    }}>
                      {step.category}
                    </span>
                    {step.requires_human && (
                      <span style={styles.stepHumanBadge}>
                        {t('workflowStudio.humanApproval', 'Human')}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Publish + Download buttons */}
          <div style={styles.publishRow}>
            <ActionButton
              label={t('workflowStudio.downloadJson', 'Download JSON')}
              onClick={handleDownloadJson}
            />
            <ActionButton
              label={
                publishStatus === 'publishing'
                  ? t('workflowStudio.publishing', 'Publishing...')
                  : t('workflowStudio.publish', 'Publish as Agent')
              }
              onClick={handlePublish}
              loading={publishStatus === 'publishing'}
              disabled={publishStatus === 'publishing'}
            />
          </div>
          {publishMessage && (
            <div style={{
              ...styles.publishMessage,
              color: publishStatus === 'success' ? '#2e7d32' : '#d32f2f',
            }}>
              {publishMessage}
            </div>
          )}
        </div>
      )}

      {/* Tab content */}
      {activeTab === 'design' && (
        <div style={styles.chatArea}>
          <ChatPanel
            messages={messages}
            onSendMessage={sendMessage}
            isLoading={isLoading}
            streamingContent={streamingContent}
            placeholder={t('workflowStudio.placeholder', 'Describe the automation you want to create...')}
          />
        </div>
      )}

      {activeTab === 'import' && (
        <div style={styles.importArea}>
          <div
            style={styles.importDropzone}
            onClick={() => fileInputRef.current?.click()}
          >
            <span style={styles.importIcon} className="material-icons">cloud_upload</span>
            <h4 style={styles.importTitle}>{t('workflowStudio.dropFile', 'Drop or click to upload')}</h4>
            <p style={styles.importDesc}>
              {t('workflowStudio.importDesc', 'Import an existing N8N workflow JSON file. The platform will analyze it and create an agent with an adapted UI.')}
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,application/json"
              style={{ display: 'none' }}
              onChange={handleFileImport}
            />
          </div>

          <span style={styles.importOr}>{t('workflowStudio.or', 'or paste JSON below')}</span>

          <div style={styles.importPasteArea}>
            <textarea
              style={styles.importTextarea}
              value={importJson}
              onChange={(e) => setImportJson(e.target.value)}
              placeholder={t('workflowStudio.pasteJson', '{"name": "...", "nodes": [...], "connections": {...}}')}
            />
            <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end' }}>
              <ActionButton
                label={t('workflowStudio.importBtn', 'Import Workflow')}
                onClick={handlePasteImport}
                disabled={!importJson.trim()}
              />
            </div>
          </div>
        </div>
      )}

      {activeTab === 'editor' && (
        <div style={styles.editorArea}>
          <iframe
            src={n8nUrl}
            style={styles.iframe}
            title="N8N Workflow Editor"
            sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
          />
        </div>
      )}
    </div>
  );
};

export default WorkflowStudioView;
