/**
 * Framework Types — Types TypeScript partagés par tous les agents.
 *
 * Ces types sont le miroir côté frontend des schemas Pydantic backend.
 * Tout agent importe uniquement depuis @framework/types.
 */

// =============================================================================
// Agent
// =============================================================================

export interface AgentManifest {
  name: string;
  slug: string;
  version: string;
  description: string;
  author: string;
  icon: string;
  category: string;
  tags: string[];
  dependencies: {
    tools: string[];
    connectors: string[];
  };
  triggers: AgentTrigger[];
  capabilities: string[];
  min_platform_version: string;
}

export interface AgentTrigger {
  type: 'user_message' | 'webhook' | 'cron' | 'event';
  config: Record<string, unknown>;
}

export type AgentLifecycle = 'draft' | 'active' | 'deprecated' | 'disabled' | 'archived';

// =============================================================================
// Messages & Responses
// =============================================================================

export interface FileAttachment {
  filename: string;
  content_type: string;
  storage_key: string;
  size_bytes: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  attachments: FileAttachment[];
  metadata: Record<string, unknown>;
  timestamp: string;
}

export interface AgentResponse {
  content: string;
  attachments: FileAttachment[];
  metadata: Record<string, unknown>;
}

export interface StreamChunk {
  job_id: string;
  content: string;
  is_final: boolean;
}

// =============================================================================
// Jobs
// =============================================================================

export type JobStatus = 'pending' | 'running' | 'streaming' | 'completed' | 'failed' | 'cancelled';

export interface JobInfo {
  job_id: string;
  status: JobStatus;
  progress: number;
  progress_message: string;
  result?: AgentResponse;
  error?: string;
}

export interface JobUpdate {
  type: 'job_update';
  job_id: string;
  status: JobStatus;
  progress: number;
  message: string;
}

// =============================================================================
// Sessions
// =============================================================================

export interface SessionInfo {
  session_id: string;
  agent_slug: string;
  user_id: number;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

// =============================================================================
// Tools & Connectors
// =============================================================================

export interface ToolParameter {
  name: string;
  type: string;
  description: string;
  required: boolean;
  default: unknown;
}

export interface ToolMetadata {
  slug: string;
  name: string;
  description: string;
  version: string;
  input_schema: ToolParameter[];
  output_schema: ToolParameter[];
  examples: Array<{
    description: string;
    input: Record<string, unknown>;
    output: Record<string, unknown>;
  }>;
}

export interface ConnectorMetadata {
  slug: string;
  name: string;
  description: string;
  version: string;
  auth_type: string;
  actions: Array<{
    name: string;
    description: string;
    input_schema: ToolParameter[];
    output_schema: ToolParameter[];
  }>;
  is_connected: boolean;
}

// =============================================================================
// Agent View Props (interface que tout frontend d'agent reçoit)
// =============================================================================

export interface AgentViewProps {
  /** Manifeste de l'agent */
  agent: AgentManifest;
  /** ID de la session courante */
  sessionId: string;
  /** ID de l'utilisateur courant */
  userId: number;
}

// =============================================================================
// WebSocket
// =============================================================================

export type WebSocketMessage = JobUpdate | StreamChunk | {
  type: 'connected';
  message: string;
};
