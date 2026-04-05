/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Mock API data for demo mode (when backend is not running).
 */

const DEMO_AGENTS = [
  {
    id: "a1b2c3d4-1111-4444-8888-000000000001",
    name: "Research Agent",
    description: "Web research, data collection, and report writing specialist",
    role: "researcher",
    status: "idle",
    is_active: true,
    llm_provider: "anthropic",
    llm_model: "claude-sonnet-4-20250514",
    system_prompt: null,
    temperature: 0.7,
    max_tokens: 4096,
    enabled_tools: { browser: true, web_search: true, web_scraper: true, word: true, pdf: true },
    max_concurrent_tasks: 3,
    tasks_completed: 47,
    tasks_failed: 2,
    email: "research-agent@whiteops.local",
    worker_id: "w1",
    created_at: "2025-03-15T09:00:00Z",
    updated_at: "2025-04-05T10:30:00Z",
  },
  {
    id: "a1b2c3d4-1111-4444-8888-000000000002",
    name: "Data Analyst",
    description: "Excel, data analysis, visualization, and financial reports",
    role: "analyst",
    status: "busy",
    is_active: true,
    llm_provider: "anthropic",
    llm_model: "claude-sonnet-4-20250514",
    system_prompt: null,
    temperature: 0.3,
    max_tokens: 4096,
    enabled_tools: { excel: true, data_analysis: true, data_visualization: true, report_generator: true },
    max_concurrent_tasks: 2,
    tasks_completed: 83,
    tasks_failed: 5,
    email: "data-analyst@whiteops.local",
    worker_id: "w1",
    created_at: "2025-03-15T09:00:00Z",
    updated_at: "2025-04-05T11:00:00Z",
  },
  {
    id: "a1b2c3d4-1111-4444-8888-000000000003",
    name: "Office Assistant",
    description: "Documents, presentations, email management, calendar",
    role: "assistant",
    status: "idle",
    is_active: true,
    llm_provider: "openai",
    llm_model: "gpt-4o",
    system_prompt: null,
    temperature: 0.7,
    max_tokens: 4096,
    enabled_tools: { word: true, powerpoint: true, pdf: true, external_email: true, calendar: true },
    max_concurrent_tasks: 5,
    tasks_completed: 124,
    tasks_failed: 3,
    email: "office-assistant@whiteops.local",
    worker_id: "w2",
    created_at: "2025-03-16T14:00:00Z",
    updated_at: "2025-04-05T09:00:00Z",
  },
  {
    id: "a1b2c3d4-1111-4444-8888-000000000004",
    name: "Developer Bot",
    description: "Code execution, API integration, technical tasks, git operations",
    role: "developer",
    status: "idle",
    is_active: true,
    llm_provider: "anthropic",
    llm_model: "claude-sonnet-4-20250514",
    system_prompt: null,
    temperature: 0.2,
    max_tokens: 8192,
    enabled_tools: { code_exec: true, api_caller: true, webhook: true, file_manager: true },
    max_concurrent_tasks: 3,
    tasks_completed: 56,
    tasks_failed: 8,
    email: "developer-bot@whiteops.local",
    worker_id: "w1",
    created_at: "2025-03-20T10:00:00Z",
    updated_at: "2025-04-05T08:00:00Z",
  },
  {
    id: "a1b2c3d4-1111-4444-8888-000000000005",
    name: "HR Coordinator",
    description: "Leave management, employee directory, onboarding, performance tracking",
    role: "hr",
    status: "offline",
    is_active: false,
    llm_provider: "ollama",
    llm_model: "llama3.2",
    system_prompt: null,
    temperature: 0.5,
    max_tokens: 4096,
    enabled_tools: { word: true, excel: true, calendar: true, internal_email: true },
    max_concurrent_tasks: 2,
    tasks_completed: 19,
    tasks_failed: 1,
    email: "hr-coordinator@whiteops.local",
    worker_id: null,
    created_at: "2025-03-25T08:00:00Z",
    updated_at: "2025-04-04T17:00:00Z",
  },
];

const DEMO_TASKS = [
  { id: "t1", title: "Generate Q1 Sales Report", description: "Create comprehensive sales report with charts and analysis", instructions: "Analyze sales data from Q1, create Excel with pivot tables, generate PDF report", status: "completed", priority: "high", agent_id: "a1b2c3d4-1111-4444-8888-000000000002", assigned_by: "u1", result: "Report generated: /files/q1-sales-report.pdf (24 pages)", error: null, output_files: [], deadline: "2025-04-01T17:00:00Z", started_at: "2025-03-28T09:00:00Z", completed_at: "2025-03-28T10:15:00Z", retry_count: 0, max_retries: 3, required_tools: ["excel", "data_analysis"], created_at: "2025-03-28T08:30:00Z", updated_at: "2025-03-28T10:15:00Z" },
  { id: "t2", title: "Research competitor pricing", description: "Scrape and compare pricing data from top 5 competitors", instructions: null, status: "in_progress", priority: "medium", agent_id: "a1b2c3d4-1111-4444-8888-000000000001", assigned_by: "u1", result: null, error: null, output_files: [], deadline: "2025-04-06T17:00:00Z", started_at: "2025-04-05T10:00:00Z", completed_at: null, retry_count: 0, max_retries: 3, required_tools: ["browser", "web_scraper"], created_at: "2025-04-05T09:30:00Z", updated_at: "2025-04-05T10:00:00Z" },
  { id: "t3", title: "Prepare board meeting presentation", description: "20-slide presentation with financial overview", instructions: "Use company template, include Q1 financials, projections for Q2", status: "assigned", priority: "critical", agent_id: "a1b2c3d4-1111-4444-8888-000000000003", assigned_by: "u1", result: null, error: null, output_files: [], deadline: "2025-04-07T09:00:00Z", started_at: null, completed_at: null, retry_count: 0, max_retries: 3, required_tools: ["powerpoint", "excel"], created_at: "2025-04-05T08:00:00Z", updated_at: "2025-04-05T08:00:00Z" },
  { id: "t4", title: "Send weekly newsletter", description: "Compile and send weekly company newsletter", instructions: null, status: "completed", priority: "medium", agent_id: "a1b2c3d4-1111-4444-8888-000000000003", assigned_by: "u1", result: "Newsletter sent to 247 recipients", error: null, output_files: [], deadline: null, started_at: "2025-04-04T14:00:00Z", completed_at: "2025-04-04T14:30:00Z", retry_count: 0, max_retries: 3, required_tools: ["external_email"], created_at: "2025-04-04T13:00:00Z", updated_at: "2025-04-04T14:30:00Z" },
  { id: "t5", title: "Fix API integration bug", description: "Debug and fix the payment gateway timeout issue", instructions: null, status: "failed", priority: "high", agent_id: "a1b2c3d4-1111-4444-8888-000000000004", assigned_by: "u1", result: null, error: "TimeoutError: Payment gateway not responding after 30s", output_files: [], deadline: null, started_at: "2025-04-05T07:00:00Z", completed_at: "2025-04-05T07:30:00Z", retry_count: 2, max_retries: 3, required_tools: ["code_exec", "api_caller"], created_at: "2025-04-05T06:00:00Z", updated_at: "2025-04-05T07:30:00Z" },
  { id: "t6", title: "Create employee onboarding checklist", description: "Word document with onboarding steps for new hires", instructions: null, status: "pending", priority: "low", agent_id: null, assigned_by: "u1", result: null, error: null, output_files: [], deadline: "2025-04-10T17:00:00Z", started_at: null, completed_at: null, retry_count: 0, max_retries: 3, required_tools: ["word"], created_at: "2025-04-05T11:00:00Z", updated_at: "2025-04-05T11:00:00Z" },
  { id: "t7", title: "Translate product brochure to Turkish", description: "Translate 10-page product brochure from English to Turkish", instructions: null, status: "completed", priority: "medium", agent_id: "a1b2c3d4-1111-4444-8888-000000000001", assigned_by: "u1", result: "Translation completed: brochure_TR.docx", error: null, output_files: [], deadline: null, started_at: "2025-04-04T09:00:00Z", completed_at: "2025-04-04T09:45:00Z", retry_count: 0, max_retries: 3, required_tools: ["translator", "word"], created_at: "2025-04-04T08:00:00Z", updated_at: "2025-04-04T09:45:00Z" },
];

const DEMO_WORKERS = [
  { id: "w1", name: "office-server-01", hostname: "DESKTOP-A1B2C3", ip_address: "192.168.1.100", status: "online", is_approved: true, group: "Main Office", max_agents: 5, cpu_usage_percent: 34.2, memory_usage_percent: 62.8, disk_usage_percent: 45.1, last_heartbeat: new Date().toISOString() },
  { id: "w2", name: "office-server-02", hostname: "DESKTOP-D4E5F6", ip_address: "192.168.1.101", status: "online", is_approved: true, group: "Main Office", max_agents: 5, cpu_usage_percent: 18.5, memory_usage_percent: 41.3, disk_usage_percent: 38.7, last_heartbeat: new Date().toISOString() },
  { id: "w3", name: "remote-worker-01", hostname: "LAPTOP-G7H8I9", ip_address: "10.0.0.50", status: "pending", is_approved: false, group: null, max_agents: 3, cpu_usage_percent: 0, memory_usage_percent: 0, disk_usage_percent: 0, last_heartbeat: new Date().toISOString() },
];

const DEMO_MESSAGES = [
  { id: "m1", sender_agent_id: "a1b2c3d4-1111-4444-8888-000000000001", recipient_agent_id: "a1b2c3d4-1111-4444-8888-000000000002", channel: "email", subject: "Competitor data ready", body: "I've finished scraping competitor pricing data. The CSV is in shared storage at /files/competitor-prices.csv. You can use it for the Q1 analysis.", is_read: true, attachments: [], created_at: "2025-04-05T10:30:00Z" },
  { id: "m2", sender_agent_id: "a1b2c3d4-1111-4444-8888-000000000002", recipient_agent_id: "a1b2c3d4-1111-4444-8888-000000000003", channel: "direct", subject: "Q1 charts for presentation", body: "The Q1 financial charts are ready. I've saved them as PNGs in /files/q1-charts/. Please include them in the board presentation.", is_read: false, attachments: [], created_at: "2025-04-05T11:00:00Z" },
  { id: "m3", sender_agent_id: "a1b2c3d4-1111-4444-8888-000000000004", recipient_agent_id: "a1b2c3d4-1111-4444-8888-000000000001", channel: "direct", subject: "API docs needed", body: "Can you research the Stripe API v2025 docs? I need the new webhook event formats for the payment integration fix.", is_read: false, attachments: [], created_at: "2025-04-05T11:15:00Z" },
];

const DEMO_FILES = [
  { id: "f1", filename: "q1-sales-report.pdf", content_type: "application/pdf", size_bytes: 2457600, task_id: "t1", tags: ["report", "q1"], created_at: "2025-03-28T10:15:00Z" },
  { id: "f2", filename: "competitor-prices.csv", content_type: "text/csv", size_bytes: 34560, task_id: "t2", tags: ["data"], created_at: "2025-04-05T10:25:00Z" },
  { id: "f3", filename: "q1-revenue-chart.png", content_type: "image/png", size_bytes: 156000, task_id: null, tags: ["chart"], created_at: "2025-04-05T11:00:00Z" },
  { id: "f4", filename: "brochure_TR.docx", content_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", size_bytes: 890000, task_id: "t7", tags: ["translation", "turkish"], created_at: "2025-04-04T09:45:00Z" },
  { id: "f5", filename: "weekly-newsletter-apr4.html", content_type: "text/html", size_bytes: 45200, task_id: "t4", tags: ["newsletter"], created_at: "2025-04-04T14:30:00Z" },
];

const DEMO_WORKFLOWS = [
  { id: "wf1", name: "Weekly Report Pipeline", description: "Collects data, analyzes trends, generates report, sends via email", status: "active", is_template: false, created_at: "2025-03-20T10:00:00Z" },
  { id: "wf2", name: "New Client Onboarding", description: "CRM entry, welcome email, document generation, calendar setup", status: "draft", is_template: true, created_at: "2025-03-25T14:00:00Z" },
];

const DEMO_KNOWLEDGE = [
  { id: "k1", title: "Company Brand Guidelines", content: "Primary color: #4c6ef5. Font: Inter. Logo usage rules...", category: "policies", tags: ["branding", "design"], source: "marketing", created_at: "2025-03-15T09:00:00Z" },
  { id: "k2", title: "Invoice Payment Terms", content: "Standard payment terms: Net 30. Early payment discount: 2/10 net 30...", category: "procedures", tags: ["finance", "invoicing"], source: "accounting", created_at: "2025-03-16T10:00:00Z" },
  { id: "k3", title: "API Rate Limits for Partners", content: "Tier 1: 1000 req/min. Tier 2: 5000 req/min. Enterprise: unlimited...", category: "technical", tags: ["api", "partners"], source: "engineering", created_at: "2025-03-20T11:00:00Z" },
];

const DEMO_COLLABORATIONS = [
  { id: "c1", name: "Q1 Report Collaboration", description: "Research, Data Analyst, and Office Assistant working on Q1 board report", status: "active", participants: ["a1b2c3d4-1111-4444-8888-000000000001", "a1b2c3d4-1111-4444-8888-000000000002", "a1b2c3d4-1111-4444-8888-000000000003"], message_count: 8, task_id: "t3", created_at: "2025-04-05T08:00:00Z", shared_context: { deadline: "2025-04-07", topic: "Q1 Board Presentation" }, messages: [{ agent_id: "a1b2c3d4-1111-4444-8888-000000000002", message: "I've finished the financial analysis. Revenue up 12% QoQ.", type: "result", timestamp: "2025-04-05T10:00:00Z" }, { agent_id: "a1b2c3d4-1111-4444-8888-000000000001", message: "Competitor analysis complete. We're #2 in market share, gaining ground.", type: "result", timestamp: "2025-04-05T10:30:00Z" }, { agent_id: "a1b2c3d4-1111-4444-8888-000000000003", message: "Building the presentation now. Should I use the blue or dark theme?", type: "question", timestamp: "2025-04-05T11:00:00Z" }] },
];

const DEMO_SETTINGS: any = {
  llm: {
    default_provider: { value: "anthropic", description: "Default LLM provider", is_secret: false, is_default: false },
    default_model: { value: "claude-sonnet-4-20250514", description: "Default LLM model", is_secret: false, is_default: false },
    anthropic_api_key: { value: "sk-a...7x2Q", description: "Anthropic API key", is_secret: true, is_default: false },
    openai_api_key: { value: "sk-p...mN3k", description: "OpenAI API key", is_secret: true, is_default: false },
    google_api_key: { value: "", description: "Google API key", is_secret: true, is_default: true },
    ollama_base_url: { value: "http://localhost:11434", description: "Ollama base URL", is_secret: false, is_default: true },
    max_tokens: { value: "4096", description: "Default max tokens per request", is_secret: false, is_default: true },
    temperature: { value: "0.7", description: "Default temperature", is_secret: false, is_default: true },
  },
  email: {
    smtp_host: { value: "smtp.gmail.com", description: "External SMTP host", is_secret: false, is_default: false },
    smtp_port: { value: "587", description: "External SMTP port", is_secret: false, is_default: true },
    smtp_user: { value: "ops@company.com", description: "SMTP username", is_secret: false, is_default: false },
    smtp_password: { value: "****", description: "SMTP password", is_secret: true, is_default: false },
    smtp_from: { value: "ops@company.com", description: "From address", is_secret: false, is_default: false },
  },
  security: {
    jwt_expire_minutes: { value: "1440", description: "JWT token expiry in minutes", is_secret: false, is_default: true },
    require_worker_approval: { value: "true", description: "New workers must be approved", is_secret: false, is_default: true },
    rate_limit_per_minute: { value: "120", description: "API rate limit per user per minute", is_secret: false, is_default: false },
    sandbox_enabled: { value: "true", description: "Enable code execution sandbox", is_secret: false, is_default: true },
  },
  general: {
    max_agents_per_worker: { value: "5", description: "Maximum agents per worker node", is_secret: false, is_default: true },
    task_timeout_minutes: { value: "60", description: "Default task timeout", is_secret: false, is_default: true },
    auto_assign_tasks: { value: "true", description: "Auto assign tasks to idle agents", is_secret: false, is_default: true },
    maintenance_mode: { value: "false", description: "Enable maintenance mode", is_secret: false, is_default: true },
    log_level: { value: "INFO", description: "System log level", is_secret: false, is_default: true },
  },
  notifications: {
    notify_task_complete: { value: "true", description: "Notify when tasks complete", is_secret: false, is_default: true },
    notify_task_failed: { value: "true", description: "Notify when tasks fail", is_secret: false, is_default: true },
    notify_worker_offline: { value: "true", description: "Notify when workers go offline", is_secret: false, is_default: true },
    webhook_url: { value: "", description: "Webhook URL for external notifications", is_secret: false, is_default: true },
  },
  storage: {
    max_file_size_mb: { value: "100", description: "Maximum file upload size in MB", is_secret: false, is_default: true },
    allowed_file_types: { value: "*", description: "Allowed file extensions", is_secret: false, is_default: true },
    auto_cleanup_days: { value: "30", description: "Auto-delete files older than N days", is_secret: false, is_default: true },
  },
};

const DEMO_DASHBOARD = {
  agents: { total: 5, active: 4, busy: 1 },
  tasks: { total: 7, by_status: { completed: 3, in_progress: 1, assigned: 1, pending: 1, failed: 1 } },
  workers: { total: 3, online: 2 },
  messages: { total: 3, unread: 2 },
};

const DEMO_ANALYTICS = {
  period_days: 7,
  tasks: { total: 34, completed: 28, failed: 3, success_rate: 82.4, avg_completion_seconds: 2340 },
  messages: { total: 45 },
  files: { total: 18, total_size_bytes: 15400000 },
};

const DEMO_AGENT_ANALYTICS = DEMO_AGENTS.map(a => ({
  id: a.id, name: a.name, role: a.role, status: a.status,
  tasks_completed: a.tasks_completed, tasks_failed: a.tasks_failed,
  total_tasks: a.tasks_completed + a.tasks_failed,
  success_rate: Math.round(a.tasks_completed / (a.tasks_completed + a.tasks_failed) * 100 * 10) / 10,
  llm_provider: a.llm_provider, llm_model: a.llm_model,
}));

const DEMO_WORKER_UTILIZATION = DEMO_WORKERS.filter(w => w.status === "online").map(w => ({
  id: w.id, name: w.name, ip_address: w.ip_address,
  cpu_percent: w.cpu_usage_percent, memory_percent: w.memory_usage_percent,
  disk_percent: w.disk_usage_percent, agents_active: 3, agents_busy: 1,
  max_agents: w.max_agents, capacity_percent: 60,
}));

const DEMO_HEALTH = {
  overall: "healthy",
  components: {
    database: { status: "healthy", type: "PostgreSQL" },
    redis: { status: "healthy" },
    storage: { status: "healthy", type: "MinIO" },
    mail: { status: "healthy" },
  },
};

const DEMO_KNOWLEDGE_CATEGORIES = [
  { category: "policies", count: 1 },
  { category: "procedures", count: 1 },
  { category: "technical", count: 1 },
];

// Mock response helper
function mock(data: any) {
  return Promise.resolve({ data });
}

/**
 * Mock API that returns demo data for all endpoints.
 */
export const mockApi = {
  auth: {
    login: () => mock({ access_token: "demo-token-xxx" }),
    me: () => mock({ id: "u1", email: "admin@whiteops.local", full_name: "System Admin", role: "admin" }),
  },
  dashboard: { overview: () => mock(DEMO_DASHBOARD) },
  agents: {
    list: () => mock(DEMO_AGENTS),
    get: (id: string) => mock(DEMO_AGENTS.find(a => a.id === id) || DEMO_AGENTS[0]),
    create: (data: any) => mock({ ...data, id: "new-" + Date.now(), status: "idle", tasks_completed: 0, tasks_failed: 0, created_at: new Date().toISOString() }),
    update: (_id: string, data: any) => mock(data),
    delete: () => mock({}),
    start: (id: string) => mock({ ...DEMO_AGENTS.find(a => a.id === id), status: "idle" }),
    stop: (id: string) => mock({ ...DEMO_AGENTS.find(a => a.id === id), status: "offline" }),
  },
  tasks: {
    list: () => mock(DEMO_TASKS),
    get: (id: string) => mock(DEMO_TASKS.find(t => t.id === id)),
    create: (data: any) => mock({ ...data, id: "t-new", status: "pending", created_at: new Date().toISOString() }),
    update: () => mock({}),
    delete: () => mock({}),
    cancel: () => mock({}),
    stats: () => mock({ total: 7, by_status: DEMO_DASHBOARD.tasks.by_status, by_priority: { critical: 1, high: 2, medium: 3, low: 1 } }),
  },
  workflows: {
    list: () => mock(DEMO_WORKFLOWS),
    get: (id: string) => mock({ ...DEMO_WORKFLOWS.find(w => w.id === id), steps: [], config: {} }),
    create: (data: any) => mock({ ...data, id: "wf-new", status: "draft" }),
    delete: () => mock({}),
  },
  messages: {
    list: () => mock(DEMO_MESSAGES),
    send: () => mock({ id: "m-new", status: "sent" }),
    markRead: () => mock({ is_read: true }),
  },
  files: {
    list: () => mock(DEMO_FILES),
    get: (id: string) => mock(DEMO_FILES.find(f => f.id === id)),
  },
  admin: {
    users: () => mock([{ id: "u1", email: "admin@whiteops.local", full_name: "System Admin", role: "admin", is_active: true, created_at: "2025-03-15T09:00:00Z" }]),
    workers: () => mock(DEMO_WORKERS),
    approveWorker: () => mock({ is_approved: true, status: "online" }),
    auditLogs: () => mock([]),
  },
  settings: {
    getAll: () => mock(DEMO_SETTINGS),
    update: () => mock({ status: "updated" }),
    bulkUpdate: () => mock({ updated: 1 }),
    health: () => mock(DEMO_HEALTH),
  },
  analytics: {
    overview: () => mock(DEMO_ANALYTICS),
    agents: () => mock(DEMO_AGENT_ANALYTICS),
    taskTimeline: () => mock([]),
    workerUtilization: () => mock(DEMO_WORKER_UTILIZATION),
  },
  knowledge: {
    list: () => mock(DEMO_KNOWLEDGE),
    get: (id: string) => mock(DEMO_KNOWLEDGE.find(k => k.id === id)),
    create: (data: any) => mock({ id: "k-new", ...data }),
    delete: () => mock({}),
    categories: () => mock(DEMO_KNOWLEDGE_CATEGORIES),
  },
  collaboration: {
    list: () => mock(DEMO_COLLABORATIONS),
    get: (id: string) => mock(DEMO_COLLABORATIONS.find(c => c.id === id) || DEMO_COLLABORATIONS[0]),
    create: (data: any) => mock({ id: "c-new", ...data, status: "active" }),
    close: () => mock({ status: "completed" }),
  },
  workers: { overview: () => mock({ total_workers: 3, online_workers: 2 }) },
};
