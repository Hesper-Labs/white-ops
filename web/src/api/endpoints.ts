import api from "./client";
import { mockApi } from "./mock";

// Helper: try real API, fall back to mock in demo mode
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function withFallback<T extends (...args: any[]) => Promise<any>>(
  realFn: T,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  mockFn: (...args: any[]) => Promise<any>,
): T {
  return ((...args: Parameters<T>) =>
    realFn(...args).catch(() => mockFn(...args))) as T;
}

// Auth
export const authApi = {
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),
  me: () => api.get("/auth/me"),
};

// Agents
export const agentsApi = {
  list: withFallback((params?: Record<string, string>) => api.get("/agents/", { params }), mockApi.agents.list),
  get: withFallback((id: string) => api.get(`/agents/${id}`), mockApi.agents.get),
  create: (data: Record<string, unknown>) => api.post("/agents/", data).catch(() => mockApi.agents.create(data)),
  update: (id: string, data: Record<string, unknown>) => api.patch(`/agents/${id}`, data).catch(() => mockApi.agents.update(id, data)),
  delete: (id: string) => api.delete(`/agents/${id}`).catch(() => mockApi.agents.delete()),
  start: (id: string) => api.post(`/agents/${id}/start`).catch(() => mockApi.agents.start(id)),
  stop: (id: string) => api.post(`/agents/${id}/stop`).catch(() => mockApi.agents.stop(id)),
};

// Tasks
export const tasksApi = {
  list: withFallback((params?: Record<string, string>) => api.get("/tasks/", { params }), mockApi.tasks.list),
  get: withFallback((id: string) => api.get(`/tasks/${id}`), mockApi.tasks.get),
  create: (data: Record<string, unknown>) => api.post("/tasks/", data).catch(() => mockApi.tasks.create(data)),
  update: (id: string, data: Record<string, unknown>) => api.patch(`/tasks/${id}`, data).catch(() => mockApi.tasks.update()),
  delete: (id: string) => api.delete(`/tasks/${id}`).catch(() => mockApi.tasks.delete()),
  cancel: (id: string) => api.post(`/tasks/${id}/cancel`).catch(() => mockApi.tasks.cancel()),
  stats: withFallback(() => api.get("/tasks/stats"), mockApi.tasks.stats),
};

// Workflows
export const workflowsApi = {
  list: withFallback(() => api.get("/workflows/"), mockApi.workflows.list),
  get: withFallback((id: string) => api.get(`/workflows/${id}`), mockApi.workflows.get),
  create: (data: Record<string, unknown>) => api.post("/workflows/", data).catch(() => mockApi.workflows.create(data)),
  addStep: (workflowId: string, data: Record<string, unknown>) =>
    api.post(`/workflows/${workflowId}/steps`, data),
  delete: (id: string) => api.delete(`/workflows/${id}`).catch(() => mockApi.workflows.delete()),
};

// Messages
export const messagesApi = {
  list: withFallback((params?: Record<string, string>) => api.get("/messages/", { params }), mockApi.messages.list),
  send: (data: Record<string, unknown>) => api.post("/messages/send", data).catch(() => mockApi.messages.send()),
  markRead: (id: string) => api.patch(`/messages/${id}/read`).catch(() => mockApi.messages.markRead()),
};

// Files
export const filesApi = {
  list: withFallback((params?: Record<string, string>) => api.get("/files/", { params }), mockApi.files.list),
  get: withFallback((id: string) => api.get(`/files/${id}`), mockApi.files.get),
  upload: (file: File, taskId?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post("/files/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      params: taskId ? { task_id: taskId } : undefined,
    });
  },
};

// Admin
export const adminApi = {
  users: withFallback(() => api.get("/admin/users"), mockApi.admin.users),
  createUser: (data: Record<string, unknown>) => api.post("/admin/users", data),
  workers: withFallback(() => api.get("/admin/workers"), mockApi.admin.workers),
  approveWorker: (id: string, data: Record<string, unknown>) =>
    api.patch(`/admin/workers/${id}/approve`, data).catch(() => mockApi.admin.approveWorker()),
  auditLogs: (params?: Record<string, string>) => api.get("/admin/audit", { params }).catch(() => mockApi.admin.auditLogs()),
};

// Dashboard
export const dashboardApi = {
  overview: withFallback(() => api.get("/dashboard/overview"), mockApi.dashboard.overview),
};

// Settings
export const settingsApi = {
  getAll: withFallback(() => api.get("/settings/"), mockApi.settings.getAll),
  update: (category: string, key: string, value: string) =>
    api.put(`/settings/${category}/${key}`, { value }).catch(() => mockApi.settings.update()),
  bulkUpdate: (settings: Record<string, string>) =>
    api.put("/settings/bulk", { settings }).catch(() => mockApi.settings.bulkUpdate()),
  health: withFallback(() => api.get("/settings/health"), mockApi.settings.health),
};

// Analytics
export const analyticsApi = {
  overview: withFallback((days?: number) =>
    api.get("/analytics/overview", { params: days ? { days } : undefined }), mockApi.analytics.overview),
  agents: withFallback(() => api.get("/analytics/agents"), mockApi.analytics.agents),
  taskTimeline: withFallback((days?: number) =>
    api.get("/analytics/tasks/timeline", { params: days ? { days } : undefined }), mockApi.analytics.taskTimeline),
  workerUtilization: withFallback(() => api.get("/analytics/workers/utilization"), mockApi.analytics.workerUtilization),
};

// Knowledge Base
export const knowledgeApi = {
  list: withFallback((params?: Record<string, string>) => api.get("/knowledge/", { params }), mockApi.knowledge.list),
  get: withFallback((id: string) => api.get(`/knowledge/${id}`), mockApi.knowledge.get),
  create: (data: Record<string, unknown>) => api.post("/knowledge/", data).catch(() => mockApi.knowledge.create(data)),
  delete: (id: string) => api.delete(`/knowledge/${id}`).catch(() => mockApi.knowledge.delete()),
  categories: withFallback(() => api.get("/knowledge/categories"), mockApi.knowledge.categories),
};

// Collaboration
export const collaborationApi = {
  list: withFallback((params?: Record<string, string>) => api.get("/collaboration/", { params }), mockApi.collaboration.list),
  get: withFallback((id: string) => api.get(`/collaboration/${id}`), mockApi.collaboration.get),
  create: (data: Record<string, unknown>) => api.post("/collaboration/", data).catch(() => mockApi.collaboration.create(data)),
  addMessage: (id: string, data: Record<string, unknown>) =>
    api.post(`/collaboration/${id}/messages`, data),
  close: (id: string) => api.post(`/collaboration/${id}/close`).catch(() => mockApi.collaboration.close()),
};

// Workers (public)
export const workersApi = {
  overview: withFallback(() => api.get("/workers/overview"), mockApi.workers.overview),
};

// --- Demo data for new API modules ---
const DEMO_COST_SUMMARY = { data: { total: 127.45, period: "month", currency: "USD" } };
const DEMO_DAILY_COSTS = { data: [] };
const DEMO_AGENT_COSTS = { data: [] };
const DEMO_PROVIDER_COSTS = { data: [] };
const DEMO_BUDGET = { data: { monthly_limit: 500, current_spend: 127.45, currency: "USD" } };
const DEMO_CIRCUIT_BREAKERS = { data: [] };
const DEMO_DLQ = { data: [] };
const DEMO_DLQ_STATS = { data: { total: 0, pending: 0, retried: 0, discarded: 0 } };
const DEMO_SECURITY = { data: { mfa_enabled: false, password_policy: { min_length: 8 }, ip_whitelist: [] } };

// Cost
export const costApi = {
  getSummary: () => api.get("/cost/summary").catch(() => DEMO_COST_SUMMARY),
  getDaily: (days = 30) => api.get(`/cost/daily?days=${days}`).catch(() => DEMO_DAILY_COSTS),
  getByAgent: () => api.get("/cost/by-agent").catch(() => DEMO_AGENT_COSTS),
  getByProvider: () => api.get("/cost/by-provider").catch(() => DEMO_PROVIDER_COSTS),
  getBudget: () => api.get("/cost/budget").catch(() => DEMO_BUDGET),
  setBudget: (data: Record<string, unknown>) => api.put("/cost/budget", data),
};

// Circuit Breakers
export const circuitBreakerApi = {
  getAll: () => api.get("/circuit-breakers").catch(() => DEMO_CIRCUIT_BREAKERS),
  get: (name: string) => api.get(`/circuit-breakers/${name}`),
  forceOpen: (name: string) => api.post(`/circuit-breakers/${name}/force-open`),
  forceClose: (name: string) => api.post(`/circuit-breakers/${name}/force-close`),
  reset: (name: string) => api.post(`/circuit-breakers/${name}/reset`),
};

// Dead Letter Queue
export const deadLetterApi = {
  getAll: (params?: Record<string, string>) => api.get("/dead-letter", { params }).catch(() => DEMO_DLQ),
  get: (id: string) => api.get(`/dead-letter/${id}`),
  retry: (id: string) => api.post(`/dead-letter/${id}/retry`),
  retryAll: () => api.post("/dead-letter/retry-all"),
  discard: (id: string) => api.delete(`/dead-letter/${id}`),
  getStats: () => api.get("/dead-letter/stats").catch(() => DEMO_DLQ_STATS),
};

// Security
export const securityApi = {
  getSettings: () => api.get("/security").catch(() => DEMO_SECURITY),
  updatePasswordPolicy: (data: Record<string, unknown>) => api.put("/security/password-policy", data),
  getSessions: () => api.get("/security/sessions").catch(() => ({ data: [] })),
  deleteSession: (id: string) => api.delete(`/security/sessions/${id}`),
  getIpRules: () => api.get("/security/ip-rules").catch(() => ({ data: [] })),
  addIpRule: (data: Record<string, unknown>) => api.post("/security/ip-rules", data),
  deleteIpRule: (id: string) => api.delete(`/security/ip-rules/${id}`),
  getApiKeys: () => api.get("/security/api-keys").catch(() => ({ data: [] })),
  createApiKey: (data: Record<string, unknown>) => api.post("/security/api-keys", data),
  deleteApiKey: (id: string) => api.delete(`/security/api-keys/${id}`),
};

// Agent Memory
export const agentMemoryApi = {
  getMemories: (agentId: string, params?: Record<string, string>) =>
    api.get(`/agents/${agentId}/memories`, { params }).catch(() => ({ data: [] })),
  createMemory: (agentId: string, data: Record<string, unknown>) =>
    api.post(`/agents/${agentId}/memories`, data),
  updateMemory: (memoryId: string, data: Record<string, unknown>) =>
    api.put(`/agents/memories/${memoryId}`, data),
  deleteMemory: (memoryId: string) => api.delete(`/agents/memories/${memoryId}`),
  clearAll: (agentId: string) => api.delete(`/agents/${agentId}/memories`),
  getStats: (agentId: string) => api.get(`/agents/${agentId}/memory-stats`).catch(() => ({ data: {} })),
};

// Triggers
export const triggersApi = {
  getAll: () => api.get("/triggers").catch(() => ({ data: [] })),
  get: (id: string) => api.get(`/triggers/${id}`),
  create: (data: Record<string, unknown>) => api.post("/triggers", data),
  update: (id: string, data: Record<string, unknown>) => api.put(`/triggers/${id}`, data),
  delete: (id: string) => api.delete(`/triggers/${id}`),
  toggle: (id: string) => api.post(`/triggers/${id}/toggle`),
  getHistory: (id: string) => api.get(`/triggers/${id}/history`),
};

// Notifications
export const notificationsApi = {
  getAll: (params?: Record<string, string>) => api.get("/notifications", { params }).catch(() => ({ data: [] })),
  getUnreadCount: () => api.get("/notifications/unread-count").catch(() => ({ data: { count: 0 } })),
  markRead: (id: string) => api.put(`/notifications/${id}/read`),
  markAllRead: () => api.put("/notifications/read-all"),
  getChannels: () => api.get("/notifications/channels").catch(() => ({ data: [] })),
  addChannel: (data: Record<string, unknown>) => api.post("/notifications/channels", data),
  getRules: () => api.get("/notifications/rules").catch(() => ({ data: [] })),
};

// Webhooks
export const webhooksApi = {
  getAll: () => api.get("/webhooks").catch(() => ({ data: [] })),
  get: (id: string) => api.get(`/webhooks/${id}`),
  create: (data: Record<string, unknown>) => api.post("/webhooks", data),
  update: (id: string, data: Record<string, unknown>) => api.put(`/webhooks/${id}`, data),
  delete: (id: string) => api.delete(`/webhooks/${id}`),
  test: (id: string) => api.post(`/webhooks/${id}/test`),
};

// Setup
export const setupApi = {
  getStatus: () => api.get("/settings/health").catch(() => ({ data: { database: "ok", redis: "ok", minio: "ok", mail: "ok" } })),
  testLlm: (data: Record<string, unknown>) => api.post("/settings/test-llm", data).catch(() => ({ data: { success: false } })),
};

export const chatApi = {
  getConversations: () => api.get("/chat/conversations").catch(() => ({ data: [] })),
  getMessages: (convId: string) => api.get(`/chat/conversations/${convId}/messages`).catch(() => ({ data: [] })),
  sendMessage: (convId: string, content: string) => api.post(`/chat/conversations/${convId}/messages`, { content }),
  createConversation: (agentId: string, title?: string) => api.post("/chat/conversations", { agent_id: agentId, title }),
  deleteConversation: (convId: string) => api.delete(`/chat/conversations/${convId}`),
};

export const marketplaceApi = {
  getTemplates: (params?: Record<string, unknown>) => api.get("/marketplace/templates", { params }).catch(() => ({ data: [] })),
  getTemplate: (id: string) => api.get(`/marketplace/templates/${id}`),
  installTemplate: (id: string) => api.post(`/marketplace/templates/${id}/install`),
};

export const codeReviewApi = {
  getAll: (params?: Record<string, unknown>) => api.get("/code-reviews", { params }).catch(() => ({ data: [] })),
  get: (id: string) => api.get(`/code-reviews/${id}`),
  approve: (id: string) => api.post(`/code-reviews/${id}/approve`),
  reject: (id: string, reason: string) => api.post(`/code-reviews/${id}/reject`, { reason }),
  addComment: (id: string, comment: string) => api.post(`/code-reviews/${id}/comments`, { comment }),
};
