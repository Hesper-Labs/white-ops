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
