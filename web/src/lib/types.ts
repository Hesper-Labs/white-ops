/* eslint-disable @typescript-eslint/no-explicit-any */

// API response types - intentionally using `any` for dynamic API data
// These map to the actual JSON shapes returned by the server

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  role: string;
  status: string;
  is_active: boolean;
  llm_provider: string;
  llm_model: string;
  system_prompt: string | null;
  temperature: number;
  max_tokens: number;
  enabled_tools: Record<string, any>;
  max_concurrent_tasks: number;
  tasks_completed: number;
  tasks_failed: number;
  email: string | null;
  worker_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  instructions: string | null;
  status: string;
  priority: string;
  agent_id: string | null;
  assigned_by: string | null;
  result: string | null;
  error: string | null;
  output_files: any[];
  deadline: string | null;
  started_at: string | null;
  completed_at: string | null;
  retry_count: number;
  max_retries: number;
  required_tools: string[];
  created_at: string;
  updated_at: string;
}

export interface Worker {
  id: string;
  name: string;
  hostname: string;
  ip_address: string;
  status: string;
  is_approved: boolean;
  group: string | null;
  max_agents: number;
  cpu_usage_percent: number;
  memory_usage_percent: number;
  disk_usage_percent: number;
  last_heartbeat: string | null;
}

export interface Message {
  id: string;
  sender_agent_id: string;
  recipient_agent_id: string;
  channel: string;
  subject: string | null;
  body: string;
  is_read: boolean;
  attachments: any[];
  created_at: string;
}

export interface FileEntry {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  task_id: string | null;
  tags: string[];
  created_at: string;
}

export interface Workflow {
  id: string;
  name: string;
  description: string | null;
  status: string;
  is_template: boolean;
  created_at: string;
}

export interface Collaboration {
  id: string;
  name: string;
  description: string | null;
  status: string;
  participants: string[];
  message_count: number;
  task_id: string | null;
  created_at: string;
}

export interface CollaborationDetail extends Collaboration {
  shared_context: Record<string, any>;
  messages: CollaborationMessage[];
}

export interface CollaborationMessage {
  agent_id: string;
  message: string;
  type: string;
  timestamp: string;
}

export interface KnowledgeEntry {
  id: string;
  title: string;
  content: string;
  category: string;
  tags: string[];
  source: string | null;
  created_at: string;
}

export interface AgentAnalytics {
  id: string;
  name: string;
  role: string;
  status: string;
  tasks_completed: number;
  tasks_failed: number;
  total_tasks: number;
  success_rate: number;
  llm_provider: string;
  llm_model: string;
}

export interface WorkerUtilization {
  id: string;
  name: string;
  ip_address: string;
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  agents_active: number;
  agents_busy: number;
  max_agents: number;
  capacity_percent: number;
}
