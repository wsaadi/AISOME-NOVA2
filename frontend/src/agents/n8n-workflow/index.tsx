/**
 * N8N Workflow Agent View — Dynamic UI renderer for published workflow agents.
 *
 * This component reads the workflow analysis from agent.config and adapts
 * the UI to match the workflow's characteristics:
 *
 * - **form**: Classic form with detected input fields → submit → show results
 * - **chat**: Chat interface for AI-powered conversational workflows
 * - **pipeline**: Step-by-step pipeline with progress and human validation points
 * - **simple**: One-click execution for trigger-only workflows
 *
 * Each mode dynamically renders the appropriate controls based on the
 * workflow analysis (inputs, steps, validations, file uploads, etc.)
 */

import React, { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { AgentViewProps, ChatMessage } from 'framework/types';
import { ChatPanel, ActionButton, MarkdownView } from 'framework/components';
import { useAgent } from 'framework/hooks';
import styles from './styles';

// ---------------------------------------------------------------------------
// Types from workflow analysis
// ---------------------------------------------------------------------------

interface WorkflowInput {
  name: string;
  type: string; // text, textarea, file, number, boolean, select, prompt
  label: string;
  description: string;
  required: boolean;
  default?: unknown;
  options?: string[];
}

interface WorkflowStep {
  order: number;
  name: string;
  category: string;
  description: string;
  requires_human: boolean;
  icon: string;
}

interface WorkflowConfig {
  n8n_workflow_id: string;
  n8n_workflow_name: string;
  ui_mode: string;
  icon: string;
  workflow_analysis: {
    trigger_type: string;
    inputs: WorkflowInput[];
    steps: WorkflowStep[];
    has_human_validation: boolean;
    has_file_upload: boolean;
    has_file_output: boolean;
    has_ai: boolean;
    has_chat: boolean;
    node_count: number;
    ui_mode: string;
    output_type: string;
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const N8NWorkflowView: React.FC<AgentViewProps> = ({ agent, sessionId }) => {
  const { t } = useTranslation();
  // n8n_workflow agents carry a `config` field injected by AgentRuntimePage
  const config = (agent as any).config as WorkflowConfig | undefined;
  const analysis = config?.workflow_analysis;
  const uiMode = analysis?.ui_mode || config?.ui_mode || 'simple';

  // Form state
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<Record<string, unknown> | null>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);

  // Pipeline state
  const [currentStep, setCurrentStep] = useState(0);

  // Chat mode
  const {
    sendMessage,
    messages,
    isLoading,
    streamingContent,
  } = useAgent(agent.slug, sessionId);

  // --- Form handlers ---
  const handleFormChange = useCallback((name: string, value: string) => {
    setFormValues(prev => ({ ...prev, [name]: value }));
  }, []);

  const handleFormSubmit = useCallback(async () => {
    const workflowId = config?.n8n_workflow_id;
    if (!workflowId) return;
    setExecuting(true);
    setExecutionResult(null);
    setExecutionError(null);

    try {
      const token = localStorage.getItem('access_token');
      const API_BASE = process.env.REACT_APP_API_URL || '';

      const response = await fetch(
        `${API_BASE}/api/n8n/workflows/${workflowId}/execute`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ input_data: formValues }),
        },
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Execution failed' }));
        throw new Error(err.detail || `Error ${response.status}`);
      }

      const data = await response.json();
      setExecutionResult(data.execution);

      // Advance pipeline steps
      if (uiMode === 'pipeline') {
        setCurrentStep(analysis?.steps?.length || 0);
      }
    } catch (err) {
      setExecutionError(err instanceof Error ? err.message : 'Execution failed');
    } finally {
      setExecuting(false);
    }
  }, [config, formValues, uiMode, analysis]);

  // --- Simple mode handler ---
  const handleSimpleExecute = useCallback(async () => {
    const workflowId = config?.n8n_workflow_id;
    if (!workflowId) return;
    setExecuting(true);
    setExecutionResult(null);
    setExecutionError(null);

    try {
      const token = localStorage.getItem('access_token');
      const API_BASE = process.env.REACT_APP_API_URL || '';

      const response = await fetch(
        `${API_BASE}/api/n8n/workflows/${workflowId}/execute`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ input_data: {} }),
        },
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Execution failed' }));
        throw new Error(err.detail || `Error ${response.status}`);
      }

      const data = await response.json();
      setExecutionResult(data.execution);
    } catch (err) {
      setExecutionError(err instanceof Error ? err.message : 'Execution failed');
    } finally {
      setExecuting(false);
    }
  }, [config]);

  // --- Format result for display ---
  const formattedResult = useMemo(() => {
    if (!executionResult) return '';
    try {
      return JSON.stringify(executionResult, null, 2);
    } catch {
      return String(executionResult);
    }
  }, [executionResult]);

  // --- Render ---
  if (!config || !analysis) {
    return (
      <div style={styles.simpleContainer}>
        <span style={styles.simpleIcon} className="material-icons">error_outline</span>
        <h3 style={styles.simpleTitle}>{t('workflowAgent.configError', 'Configuration Error')}</h3>
        <p style={styles.simpleDesc}>
          {t('workflowAgent.noConfig', 'This agent is missing its workflow configuration.')}
        </p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.headerIcon}>
            <span className="material-icons" style={{ fontSize: 18 }}>
              {config.icon || 'account_tree'}
            </span>
          </div>
          <div>
            <h3 style={styles.headerTitle}>{agent.name}</h3>
            <p style={styles.headerDesc}>{agent.description}</p>
          </div>
        </div>
        <span style={styles.headerBadge}>
          {analysis.node_count} {t('workflowAgent.nodes', 'nodes')}
        </span>
      </div>

      {/* Content area — switches based on UI mode */}
      <div style={styles.content}>

        {/* ===== FORM MODE ===== */}
        {uiMode === 'form' && (
          <div style={styles.formContainer}>
            <div style={styles.formTitle}>
              {config.n8n_workflow_name || agent.name}
            </div>
            {agent.description && (
              <div style={styles.formDesc}>{agent.description}</div>
            )}

            {/* Dynamic form fields */}
            {analysis.inputs.map((input) => (
              <div key={input.name} style={styles.formField}>
                <label style={styles.formLabel}>
                  {input.label}
                  {input.required && <span style={styles.formRequired}>*</span>}
                </label>
                {input.description && (
                  <span style={styles.formHint}>{input.description}</span>
                )}

                {input.type === 'text' && (
                  <input
                    type="text"
                    style={styles.formInput}
                    value={formValues[input.name] || ''}
                    onChange={(e) => handleFormChange(input.name, e.target.value)}
                    placeholder={input.label}
                  />
                )}

                {(input.type === 'textarea' || input.type === 'prompt') && (
                  <textarea
                    style={styles.formTextarea}
                    value={formValues[input.name] || ''}
                    onChange={(e) => handleFormChange(input.name, e.target.value)}
                    placeholder={input.description || input.label}
                  />
                )}

                {input.type === 'number' && (
                  <input
                    type="number"
                    style={styles.formInput}
                    value={formValues[input.name] || ''}
                    onChange={(e) => handleFormChange(input.name, e.target.value)}
                  />
                )}

                {input.type === 'select' && (
                  <select
                    style={styles.formSelect}
                    value={formValues[input.name] || ''}
                    onChange={(e) => handleFormChange(input.name, e.target.value)}
                  >
                    <option value="">{t('workflowAgent.selectOption', '-- Select --')}</option>
                    {(input.options || []).map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                )}

                {input.type === 'file' && (
                  <input
                    type="file"
                    style={styles.formFileInput}
                  />
                )}

                {input.type === 'boolean' && (
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                    <input
                      type="checkbox"
                      checked={formValues[input.name] === 'true'}
                      onChange={(e) => handleFormChange(input.name, String(e.target.checked))}
                    />
                    {input.label}
                  </label>
                )}
              </div>
            ))}

            <div style={styles.formSubmitRow}>
              <ActionButton
                label={executing
                  ? t('workflowAgent.executing', 'Executing...')
                  : t('workflowAgent.execute', 'Execute Workflow')
                }
                onClick={handleFormSubmit}
                loading={executing}
                disabled={executing}
              />
            </div>
          </div>
        )}

        {/* ===== CHAT MODE ===== */}
        {uiMode === 'chat' && (
          <div style={styles.chatContainer}>
            <ChatPanel
              messages={messages}
              onSendMessage={async (content) => {
                await sendMessage(content);
              }}
              isLoading={isLoading}
              streamingContent={streamingContent}
              placeholder={t('workflowAgent.chatPlaceholder', 'Type your message...')}
            />
          </div>
        )}

        {/* ===== PIPELINE MODE ===== */}
        {uiMode === 'pipeline' && (
          <div style={styles.pipelineContainer}>
            {/* Input form at top (if inputs exist) */}
            {analysis.inputs.length > 0 && currentStep === 0 && (
              <div style={{ marginBottom: 24 }}>
                {analysis.inputs.map((input) => (
                  <div key={input.name} style={{ ...styles.formField, marginBottom: 12 }}>
                    <label style={styles.formLabel}>
                      {input.label}
                      {input.required && <span style={styles.formRequired}>*</span>}
                    </label>
                    {input.type === 'textarea' || input.type === 'prompt' ? (
                      <textarea
                        style={styles.formTextarea}
                        value={formValues[input.name] || ''}
                        onChange={(e) => handleFormChange(input.name, e.target.value)}
                        placeholder={input.description || input.label}
                      />
                    ) : (
                      <input
                        type={input.type === 'number' ? 'number' : 'text'}
                        style={styles.formInput}
                        value={formValues[input.name] || ''}
                        onChange={(e) => handleFormChange(input.name, e.target.value)}
                        placeholder={input.label}
                      />
                    )}
                  </div>
                ))}
                <div style={styles.formSubmitRow}>
                  <ActionButton
                    label={executing
                      ? t('workflowAgent.executing', 'Executing...')
                      : t('workflowAgent.startPipeline', 'Start Pipeline')
                    }
                    onClick={handleFormSubmit}
                    loading={executing}
                    disabled={executing}
                  />
                </div>
              </div>
            )}

            {/* Pipeline steps */}
            {analysis.steps.map((step, idx) => {
              const isLast = idx === analysis.steps.length - 1;
              const isDone = idx < currentStep;
              const isActive = idx === currentStep && executing;

              return (
                <div key={step.order} style={styles.pipelineStep}>
                  {/* Connecting line */}
                  {!isLast && (
                    <div style={{
                      ...styles.pipelineStepLine,
                      backgroundColor: isDone ? '#059669' : 'var(--divider-color, #e0e0e0)',
                    }} />
                  )}

                  {/* Step dot */}
                  <div style={{
                    ...styles.pipelineStepDot,
                    ...(isDone
                      ? styles.pipelineStepDotDone
                      : isActive
                        ? styles.pipelineStepDotActive
                        : styles.pipelineStepDotPending),
                  }}>
                    {isDone ? (
                      <span className="material-icons" style={{ fontSize: 16 }}>check</span>
                    ) : (
                      step.order
                    )}
                  </div>

                  {/* Step content */}
                  <div style={styles.pipelineStepContent}>
                    <div style={styles.pipelineStepName}>{step.name}</div>
                    <div style={styles.pipelineStepDesc}>{step.description}</div>
                    {step.requires_human && (
                      <div style={styles.pipelineStepHuman}>
                        {t('workflowAgent.humanRequired', 'This step requires human approval before continuing')}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ===== SIMPLE MODE ===== */}
        {uiMode === 'simple' && !executionResult && !executionError && (
          <div style={styles.simpleContainer}>
            <span style={styles.simpleIcon} className="material-icons">
              {config.icon || 'play_circle'}
            </span>
            <h3 style={styles.simpleTitle}>{agent.name}</h3>
            <p style={styles.simpleDesc}>
              {agent.description || t('workflowAgent.simpleDesc', 'Click the button to execute this workflow')}
            </p>
            <ActionButton
              label={executing
                ? t('workflowAgent.executing', 'Executing...')
                : t('workflowAgent.execute', 'Execute Workflow')
              }
              onClick={handleSimpleExecute}
              loading={executing}
              disabled={executing}
            />
          </div>
        )}

        {/* ===== Executing overlay ===== */}
        {executing && uiMode !== 'form' && uiMode !== 'pipeline' && (
          <div style={styles.executingOverlay}>
            <div style={styles.spinner} />
            <div style={styles.executingText}>
              {t('workflowAgent.executingWorkflow', 'Executing workflow...')}
            </div>
          </div>
        )}

        {/* ===== Execution Result ===== */}
        {executionResult && uiMode !== 'chat' && (
          <div style={styles.resultContainer}>
            <div style={styles.resultHeader}>
              <span className="material-icons" style={styles.resultIcon}>check_circle</span>
              <span style={styles.resultTitle}>
                {t('workflowAgent.executionComplete', 'Execution Complete')}
              </span>
            </div>
            <div style={styles.resultContent}>
              {formattedResult}
            </div>
            <div style={{ marginTop: 12, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <ActionButton
                label={t('workflowAgent.runAgain', 'Run Again')}
                onClick={() => {
                  setExecutionResult(null);
                  setExecutionError(null);
                  setCurrentStep(0);
                }}
              />
            </div>
          </div>
        )}

        {/* ===== Execution Error ===== */}
        {executionError && (
          <div style={styles.resultContainer}>
            <div style={styles.resultError}>
              <strong>{t('workflowAgent.executionFailed', 'Execution Failed')}</strong>
              <br />
              {executionError}
            </div>
            <div style={{ marginTop: 12, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <ActionButton
                label={t('workflowAgent.retry', 'Retry')}
                onClick={() => {
                  setExecutionError(null);
                  if (uiMode === 'simple') handleSimpleExecute();
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default N8NWorkflowView;
