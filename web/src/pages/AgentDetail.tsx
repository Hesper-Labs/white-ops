import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Play,
  Square,
  Copy,
  Trash2,
  Bot,
  Settings,
  Wrench,
  ScrollText,
  BarChart3,
  Save,
  Mail,
  Brain,
  Calendar,
  CheckCircle2,
  XCircle,
  Clock,
  Zap,
  DollarSign,
  Cpu,
} from "lucide-react";
import { agentsApi } from "../api/endpoints";
import { formatDate } from "../lib/utils";
import toast from "react-hot-toast";

const statusMap: Record<string, { badge: string; dot: string }> = {
  idle: { badge: "badge-green", dot: "online" },
  busy: { badge: "badge-yellow", dot: "busy" },
  error: { badge: "badge-red", dot: "error" },
  offline: { badge: "badge-gray", dot: "offline" },
  paused: { badge: "badge-blue", dot: "offline" },
};

const roleColors: Record<string, string> = {
  researcher: "badge-blue",
  analyst: "badge-yellow",
  assistant: "badge-green",
  developer: "badge-gray",
  hr: "badge-red",
  general: "badge-gray",
  writer: "badge-blue",
  accountant: "badge-yellow",
};

const TABS = ["Overview", "Configuration", "Tools", "Logs", "Performance"] as const;
type Tab = (typeof TABS)[number];

const TAB_ICONS: Record<Tab, React.ReactNode> = {
  Overview: <Bot className="h-3.5 w-3.5" />,
  Configuration: <Settings className="h-3.5 w-3.5" />,
  Tools: <Wrench className="h-3.5 w-3.5" />,
  Logs: <ScrollText className="h-3.5 w-3.5" />,
  Performance: <BarChart3 className="h-3.5 w-3.5" />,
};

const TOOL_CATEGORIES: Record<string, string[]> = {
  office: ["word", "excel", "powerpoint", "pdf", "onenote", "outlook"],
  communication: ["internal_email", "external_email", "slack", "teams", "sms", "notification"],
  research: ["browser", "web_search", "web_scraper", "news_aggregator", "academic_search"],
  data: ["data_analysis", "data_visualization", "data_cleaning", "data_export", "report_generator", "dashboard_builder"],
  filesystem: ["file_manager", "file_search", "file_converter", "archive", "cloud_storage"],
  business: ["crm", "erp", "project_management", "invoice_generator", "contract_manager", "inventory"],
  technical: ["code_exec", "api_caller", "webhook", "database_query", "git", "docker", "ci_cd"],
  finance: ["accounting", "expense_tracker", "payroll", "tax_calculator", "budget_planner"],
  hr: ["leave_management", "employee_directory", "onboarding", "performance_review", "recruitment"],
  integrations: ["calendar", "translator", "ocr", "speech_to_text", "image_generator", "scheduler"],
};

const MOCK_LOGS = [
  { ts: "2025-04-05T10:30:12Z", tool: "web_search", input: 'query="Q1 2025 market trends"', status: "ok", duration: "1.2s" },
  { ts: "2025-04-05T10:30:14Z", tool: "browser", input: "url=https://example.com/report", status: "ok", duration: "3.4s" },
  { ts: "2025-04-05T10:30:18Z", tool: "web_scraper", input: "selector=.data-table, format=json", status: "ok", duration: "2.1s" },
  { ts: "2025-04-05T10:30:21Z", tool: "data_analysis", input: "analyze competitor_prices.csv", status: "ok", duration: "4.7s" },
  { ts: "2025-04-05T10:30:26Z", tool: "excel", input: "create pivot_table from analysis", status: "ok", duration: "1.8s" },
  { ts: "2025-04-05T10:30:28Z", tool: "data_visualization", input: "chart=bar, data=revenue_by_region", status: "ok", duration: "2.3s" },
  { ts: "2025-04-05T10:30:31Z", tool: "pdf", input: "generate report.pdf from template", status: "ok", duration: "3.9s" },
  { ts: "2025-04-05T10:30:35Z", tool: "internal_email", input: "to=data-analyst, subject=Report ready", status: "ok", duration: "0.8s" },
  { ts: "2025-04-05T10:30:36Z", tool: "file_manager", input: "save /output/q1-report.pdf", status: "ok", duration: "0.3s" },
  { ts: "2025-04-05T10:31:00Z", tool: "web_search", input: 'query="competitor pricing API 2025"', status: "error", duration: "5.0s" },
];

const MOCK_PERFORMANCE = {
  tasksPerDay: [
    { day: "Mon", count: 8 },
    { day: "Tue", count: 12 },
    { day: "Wed", count: 6 },
    { day: "Thu", count: 15 },
    { day: "Fri", count: 10 },
    { day: "Sat", count: 3 },
    { day: "Sun", count: 1 },
  ],
  avgCompletionTime: "23m 40s",
  totalTokensUsed: 1_284_500,
  estimatedCost: "$18.42",
  successRate: 95.9,
  avgTokensPerTask: 23_354,
  peakHour: "10:00 - 11:00",
  totalTasks: 55,
};

export default function AgentDetail() {
  const { agentId } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["agent", agentId],
    queryFn: () => agentsApi.get(agentId!),
    enabled: !!agentId,
  });

  const startMut = useMutation({
    mutationFn: (id: string) => agentsApi.start(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["agent", agentId] }); toast.success("Agent started"); },
  });
  const stopMut = useMutation({
    mutationFn: (id: string) => agentsApi.stop(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["agent", agentId] }); toast.success("Agent stopped"); },
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => agentsApi.delete(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["agents"] }); toast.success("Agent deleted"); navigate("/agents"); },
  });

  const agent: any = data?.data ?? null;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin" />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="card p-12 text-center">
        <Bot className="h-10 w-10 text-neutral-300 mx-auto mb-3" />
        <p className="text-sm font-medium text-neutral-600">Agent not found</p>
        <button className="btn-secondary mt-4" onClick={() => navigate("/agents")}>Back to Agents</button>
      </div>
    );
  }

  const st = statusMap[agent.status as string] ?? { badge: "badge-gray", dot: "offline" };
  const roleBadge = roleColors[agent.role as string] ?? "badge-gray";
  const isRunning = agent.status !== "offline" && agent.status !== "paused";

  return (
    <div>
      {/* Back nav */}
      <button onClick={() => navigate("/agents")} className="btn-ghost flex items-center gap-1.5 mb-4 text-neutral-500 hover:text-neutral-900">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to Agents
      </button>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center">
            <Bot className="h-5 w-5 text-neutral-500" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-neutral-900">{agent.name}</h1>
              <div className={`status-dot ${st.dot}`} />
              <span className={st.badge}>{agent.status}</span>
              <span className={roleBadge}>{agent.role}</span>
            </div>
            <p className="text-xs text-neutral-400 mt-0.5">{agent.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isRunning ? (
            <button className="btn-secondary flex items-center gap-1.5" onClick={() => stopMut.mutate(agent.id)}>
              <Square className="h-3.5 w-3.5" /> Stop
            </button>
          ) : (
            <button className="btn-primary flex items-center gap-1.5" onClick={() => startMut.mutate(agent.id)}>
              <Play className="h-3.5 w-3.5" /> Start
            </button>
          )}
          <button className="btn-secondary flex items-center gap-1.5" onClick={() => toast.success("Agent cloned (demo)")}>
            <Copy className="h-3.5 w-3.5" /> Clone Agent
          </button>
          <button
            className="btn-ghost text-red-400 hover:text-red-600 flex items-center gap-1.5"
            onClick={() => { if (confirm("Delete this agent?")) deleteMut.mutate(agent.id); }}
          >
            <Trash2 className="h-3.5 w-3.5" /> Delete
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-neutral-200 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? "border-neutral-900 text-neutral-900"
                : "border-transparent text-neutral-400 hover:text-neutral-600"
            }`}
          >
            {TAB_ICONS[tab]} {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "Overview" && <OverviewTab agent={agent} />}
      {activeTab === "Configuration" && <ConfigurationTab agent={agent} />}
      {activeTab === "Tools" && <ToolsTab agent={agent} />}
      {activeTab === "Logs" && <LogsTab />}
      {activeTab === "Performance" && <PerformanceTab />}
    </div>
  );
}

/* ---------- Overview Tab ---------- */
function OverviewTab({ agent }: { agent: any }) {
  const total = (agent.tasks_completed ?? 0) + (agent.tasks_failed ?? 0);
  const successRate = total > 0 ? ((agent.tasks_completed / total) * 100).toFixed(1) : "0.0";

  return (
    <div className="space-y-6">
      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            <span className="text-xs text-neutral-400">Completed</span>
          </div>
          <p className="text-2xl font-bold text-neutral-900">{agent.tasks_completed ?? 0}</p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <XCircle className="h-4 w-4 text-red-500" />
            <span className="text-xs text-neutral-400">Failed</span>
          </div>
          <p className="text-2xl font-bold text-neutral-900">{agent.tasks_failed ?? 0}</p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="h-4 w-4 text-amber-500" />
            <span className="text-xs text-neutral-400">Success Rate</span>
          </div>
          <p className="text-2xl font-bold text-neutral-900">{successRate}%</p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="h-4 w-4 text-blue-500" />
            <span className="text-xs text-neutral-400">Total Tasks</span>
          </div>
          <p className="text-2xl font-bold text-neutral-900">{total}</p>
        </div>
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-2 gap-6">
        <div className="card p-5 space-y-4">
          <h3 className="text-sm font-semibold text-neutral-900">Agent Information</h3>
          <div className="space-y-3">
            <InfoRow icon={<Bot className="h-3.5 w-3.5" />} label="Name" value={agent.name} />
            <InfoRow icon={<Mail className="h-3.5 w-3.5" />} label="Email" value={agent.email ?? "N/A"} />
            <InfoRow icon={<Brain className="h-3.5 w-3.5" />} label="LLM Provider" value={agent.llm_provider} />
            <InfoRow icon={<Cpu className="h-3.5 w-3.5" />} label="Model" value={agent.llm_model} />
            <InfoRow icon={<Calendar className="h-3.5 w-3.5" />} label="Created" value={formatDate(agent.created_at)} />
          </div>
        </div>
        <div className="card p-5 space-y-4">
          <h3 className="text-sm font-semibold text-neutral-900">Description</h3>
          <p className="text-sm text-neutral-600 leading-relaxed">{agent.description || "No description provided."}</p>
          <h3 className="text-sm font-semibold text-neutral-900 pt-2">System Prompt</h3>
          <p className="text-sm text-neutral-500 font-mono bg-neutral-50 rounded p-3 text-xs leading-relaxed">
            {agent.system_prompt || "Default system prompt (not customized)"}
          </p>
        </div>
      </div>
    </div>
  );
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-neutral-400">{icon}</span>
      <span className="text-xs text-neutral-400 w-24">{label}</span>
      <span className="text-sm text-neutral-700 font-medium">{value}</span>
    </div>
  );
}

/* ---------- Configuration Tab ---------- */
function ConfigurationTab({ agent }: { agent: any }) {
  const [form, setForm] = useState({
    name: agent.name ?? "",
    description: agent.description ?? "",
    role: agent.role ?? "general",
    system_prompt: agent.system_prompt ?? "",
    llm_provider: agent.llm_provider ?? "anthropic",
    llm_model: agent.llm_model ?? "",
    temperature: agent.temperature ?? 0.7,
    max_tokens: agent.max_tokens ?? 4096,
  });

  const queryClient = useQueryClient();
  const updateMut = useMutation({
    mutationFn: (data: Record<string, unknown>) => agentsApi.update(agent.id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["agent", agent.id] }); toast.success("Configuration saved"); },
    onError: () => toast.error("Failed to save"),
  });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    updateMut.mutate(form);
  };

  const set = (key: string, value: any) => setForm((f) => ({ ...f, [key]: value }));

  return (
    <form onSubmit={handleSave} className="space-y-6 max-w-2xl">
      <div className="card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-neutral-900">General</h3>
        <div>
          <label className="block text-xs font-medium text-neutral-500 mb-1">Name</label>
          <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} required />
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-500 mb-1">Description</label>
          <input className="input" value={form.description} onChange={(e) => set("description", e.target.value)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-500 mb-1">Role</label>
          <select className="input" value={form.role} onChange={(e) => set("role", e.target.value)}>
            <option value="general">General</option>
            <option value="researcher">Researcher</option>
            <option value="analyst">Data Analyst</option>
            <option value="writer">Writer</option>
            <option value="developer">Developer</option>
            <option value="assistant">Executive Assistant</option>
            <option value="accountant">Accountant</option>
            <option value="hr">HR Specialist</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-500 mb-1">System Prompt</label>
          <textarea
            className="input font-mono text-xs"
            rows={6}
            value={form.system_prompt}
            onChange={(e) => set("system_prompt", e.target.value)}
            placeholder="Custom system prompt for this agent..."
          />
        </div>
      </div>

      <div className="card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-neutral-900">LLM Settings</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-neutral-500 mb-1">Provider</label>
            <select className="input" value={form.llm_provider} onChange={(e) => set("llm_provider", e.target.value)}>
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="openai">OpenAI (GPT)</option>
              <option value="google">Google (Gemini)</option>
              <option value="ollama">Ollama (Local)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-500 mb-1">Model</label>
            <input className="input font-mono text-xs" value={form.llm_model} onChange={(e) => set("llm_model", e.target.value)} />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-500 mb-1">
            Temperature: <span className="font-bold text-neutral-700">{form.temperature}</span>
          </label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={form.temperature}
            onChange={(e) => set("temperature", parseFloat(e.target.value))}
            className="w-full h-1.5 bg-neutral-200 rounded-lg appearance-none cursor-pointer accent-neutral-900"
          />
          <div className="flex justify-between text-[10px] text-neutral-300 mt-1">
            <span>0 (Precise)</span>
            <span>1 (Creative)</span>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-500 mb-1">Max Tokens</label>
          <input
            className="input"
            type="number"
            min={256}
            max={128000}
            value={form.max_tokens}
            onChange={(e) => set("max_tokens", parseInt(e.target.value) || 4096)}
          />
        </div>
      </div>

      <div className="flex gap-2">
        <button type="submit" className="btn-primary flex items-center gap-1.5" disabled={updateMut.isPending}>
          <Save className="h-3.5 w-3.5" /> {updateMut.isPending ? "Saving..." : "Save Configuration"}
        </button>
        <button type="button" className="btn-secondary" onClick={() => setForm({
          name: agent.name ?? "",
          description: agent.description ?? "",
          role: agent.role ?? "general",
          system_prompt: agent.system_prompt ?? "",
          llm_provider: agent.llm_provider ?? "anthropic",
          llm_model: agent.llm_model ?? "",
          temperature: agent.temperature ?? 0.7,
          max_tokens: agent.max_tokens ?? 4096,
        })}>
          Reset
        </button>
      </div>
    </form>
  );
}

/* ---------- Tools Tab ---------- */
function ToolsTab({ agent }: { agent: any }) {
  const enabledTools: Record<string, boolean> = agent.enabled_tools ?? {};
  const [tools, setTools] = useState<Record<string, boolean>>(() => {
    const all: Record<string, boolean> = {};
    Object.values(TOOL_CATEGORIES).flat().forEach((t) => {
      all[t] = enabledTools[t] ?? false;
    });
    return all;
  });

  const queryClient = useQueryClient();
  const updateMut = useMutation({
    mutationFn: (data: Record<string, unknown>) => agentsApi.update(agent.id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["agent", agent.id] }); toast.success("Tools saved"); },
  });

  const toggle = (tool: string) => setTools((prev) => ({ ...prev, [tool]: !prev[tool] }));
  const enabledCount = Object.values(tools).filter(Boolean).length;
  const totalCount = Object.keys(tools).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-xs text-neutral-400">
          {enabledCount} of {totalCount} tools enabled
        </p>
        <button
          className="btn-primary flex items-center gap-1.5"
          onClick={() => updateMut.mutate({ enabled_tools: tools })}
          disabled={updateMut.isPending}
        >
          <Save className="h-3.5 w-3.5" /> {updateMut.isPending ? "Saving..." : "Save Tools"}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {Object.entries(TOOL_CATEGORIES).map(([category, categoryTools]) => (
          <div key={category} className="card p-4">
            <h4 className="text-xs font-semibold text-neutral-900 uppercase tracking-wide mb-3 capitalize">{category}</h4>
            <div className="space-y-2">
              {categoryTools.map((tool) => (
                <label key={tool} className="flex items-center gap-2.5 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={tools[tool] ?? false}
                    onChange={() => toggle(tool)}
                    className="w-3.5 h-3.5 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900 cursor-pointer"
                  />
                  <span className="text-xs text-neutral-600 group-hover:text-neutral-900 font-mono">
                    {tool}
                  </span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- Logs Tab ---------- */
function LogsTab() {
  return (
    <div className="card overflow-hidden">
      <div className="bg-neutral-900 rounded-lg p-4 font-mono text-xs leading-relaxed overflow-x-auto">
        {MOCK_LOGS.map((log, i) => {
          const time = new Date(log.ts).toLocaleTimeString("en-US", { hour12: false });
          const color = log.status === "ok" ? "text-emerald-400" : "text-red-400";
          return (
            <div key={i} className="flex gap-3 hover:bg-neutral-800 px-2 py-0.5 rounded">
              <span className="text-neutral-500 shrink-0">{time}</span>
              <span className={`${color} shrink-0`}>[{log.status.toUpperCase().padEnd(5)}]</span>
              <span className="text-cyan-400 shrink-0 w-28">{log.tool}</span>
              <span className="text-neutral-300">{log.input}</span>
              <span className="text-neutral-500 ml-auto shrink-0">{log.duration}</span>
            </div>
          );
        })}
        <div className="flex gap-3 px-2 py-0.5 mt-2 text-neutral-500">
          <span>---</span>
          <span>End of log (10 entries)</span>
        </div>
      </div>
    </div>
  );
}

/* ---------- Performance Tab ---------- */
function PerformanceTab() {
  const perf = MOCK_PERFORMANCE;
  const maxCount = Math.max(...perf.tasksPerDay.map((d) => d.count));

  return (
    <div className="space-y-6">
      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="h-4 w-4 text-amber-500" />
            <span className="text-xs text-neutral-400">Total Tasks</span>
          </div>
          <p className="text-2xl font-bold text-neutral-900">{perf.totalTasks}</p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="h-4 w-4 text-blue-500" />
            <span className="text-xs text-neutral-400">Avg Completion</span>
          </div>
          <p className="text-2xl font-bold text-neutral-900">{perf.avgCompletionTime}</p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Brain className="h-4 w-4 text-purple-500" />
            <span className="text-xs text-neutral-400">Tokens Used</span>
          </div>
          <p className="text-2xl font-bold text-neutral-900">{(perf.totalTokensUsed / 1_000_000).toFixed(2)}M</p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="h-4 w-4 text-emerald-500" />
            <span className="text-xs text-neutral-400">Estimated Cost</span>
          </div>
          <p className="text-2xl font-bold text-neutral-900">{perf.estimatedCost}</p>
        </div>
      </div>

      {/* Tasks per day bar chart */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-neutral-900 mb-4">Tasks per Day (Last 7 Days)</h3>
        <div className="flex items-end gap-3 h-32">
          {perf.tasksPerDay.map((d) => (
            <div key={d.day} className="flex-1 flex flex-col items-center gap-1">
              <span className="text-xs font-medium text-neutral-900">{d.count}</span>
              <div
                className="w-full bg-neutral-200 rounded-t"
                style={{ height: `${(d.count / maxCount) * 100}%`, minHeight: 4 }}
              />
              <span className="text-[10px] text-neutral-400">{d.day}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Extra stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card p-4">
          <span className="text-xs text-neutral-400">Success Rate</span>
          <p className="text-lg font-bold text-neutral-900 mt-1">{perf.successRate}%</p>
        </div>
        <div className="card p-4">
          <span className="text-xs text-neutral-400">Avg Tokens / Task</span>
          <p className="text-lg font-bold text-neutral-900 mt-1">{perf.avgTokensPerTask.toLocaleString()}</p>
        </div>
        <div className="card p-4">
          <span className="text-xs text-neutral-400">Peak Hour</span>
          <p className="text-lg font-bold text-neutral-900 mt-1">{perf.peakHour}</p>
        </div>
      </div>
    </div>
  );
}
