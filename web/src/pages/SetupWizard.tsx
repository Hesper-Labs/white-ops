import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ChevronRight,
  ChevronLeft,
  Check,
  X,
  Server,
  Brain,
  Shield,
  Bot,
  Bell,
  Rocket,
  Copy,
  RefreshCw,
  Zap,
  CheckCircle2,
  Monitor,
  Eye,
  EyeOff,
  Database,
  HardDrive,
  Mail,
  Terminal,
  Globe,
  MessageSquare,
  Search,
  BarChart3,
  Cloud,
  Briefcase,
  FileText,
  AlertTriangle,
  Cpu,
  ExternalLink,
  Info,
  Play,
  BookOpen,
  DollarSign,
  Lock,
  FileCode,
} from "lucide-react";
import api from "../api/client";
import { cn } from "../lib/utils";
import toast from "react-hot-toast";

// ─── Types ───────────────────────────────────────────────────────────────────

interface SystemHealth {
  database: boolean;
  redis: boolean;
  minio: boolean;
  mail: boolean;
}

interface AdminForm {
  email: string;
  fullName: string;
  password: string;
  confirmPassword: string;
}

type LLMProvider = "anthropic" | "openai" | "google" | "ollama";

interface LLMConfig {
  provider: LLMProvider;
  apiKey: string;
  model: string;
  temperature: number;
}

interface WorkerInfo {
  name: string;
  ip: string;
  status: "online" | "pending" | "offline";
  cpu: number;
  memory: number;
  agents: number;
}

interface AgentForm {
  name: string;
  description: string;
  role: string;
  tools: Record<string, boolean>;
  systemPrompt: string;
}

interface NotificationForm {
  slackWebhook: string;
  emailEnabled: boolean;
  smtpHost: string;
  smtpPort: string;
  telegramToken: string;
}

type WizardData = {
  admin: AdminForm;
  llm: LLMConfig;
  agent: AgentForm;
  notifications: NotificationForm;
};

// ─── Constants ───────────────────────────────────────────────────────────────

const STEPS = [
  { label: "Welcome", icon: Rocket },
  { label: "Admin", icon: Shield },
  { label: "LLM", icon: Brain },
  { label: "Workers", icon: Server },
  { label: "Agent", icon: Bot },
  { label: "Notifications", icon: Bell },
  { label: "Complete", icon: CheckCircle2 },
];

const MODEL_OPTIONS: Record<LLMProvider, string[]> = {
  anthropic: ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-haiku-4-5-20251001"],
  openai: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
  google: ["gemini-2.0-flash", "gemini-2.5-pro"],
  ollama: ["llama3.1", "codellama", "mistral"],
};

const PROVIDER_INFO: Record<LLMProvider, { name: string; recommended?: boolean }> = {
  anthropic: { name: "Anthropic Claude", recommended: true },
  openai: { name: "OpenAI" },
  google: { name: "Google Gemini" },
  ollama: { name: "Ollama (Local)" },
};

const TOOL_CATEGORIES: { key: string; label: string; icon: React.ElementType; items: string[] }[] = [
  { key: "office", label: "Office", icon: FileText, items: ["Excel", "Word", "PowerPoint", "PDF"] },
  { key: "communication", label: "Communication", icon: MessageSquare, items: ["Email", "Slack", "Teams"] },
  { key: "research", label: "Research", icon: Search, items: ["Browser", "Search", "Scraper"] },
  { key: "data", label: "Data", icon: BarChart3, items: ["Analysis", "Database", "Visualization"] },
  { key: "technical", label: "Technical", icon: Terminal, items: ["Shell", "Git", "Docker", "Claude Code"] },
  { key: "devops", label: "DevOps", icon: Cloud, items: ["Terraform", "CI/CD", "Kubernetes"] },
  { key: "business", label: "Business", icon: Briefcase, items: ["CRM", "Invoice", "Time Tracker"] },
];

const DEMO_WORKERS: WorkerInfo[] = [];

const STORAGE_KEY = "whiteops_setup";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getPasswordStrength(pw: string): { level: string; score: number; color: string } {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[a-z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 2) return { level: "weak", score, color: "bg-red-500" };
  if (score <= 3) return { level: "fair", score, color: "bg-amber-500" };
  if (score <= 4) return { level: "good", score, color: "bg-blue-500" };
  return { level: "strong", score, color: "bg-green-500" };
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function SetupWizard() {
  const navigate = useNavigate();

  // Restore saved state
  const loadSaved = (): { step: number; data: WizardData } => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch {
      /* ignore */
    }
    return {
      step: 0,
      data: {
        admin: { email: "", fullName: "", password: "", confirmPassword: "" },
        llm: { provider: "anthropic", apiKey: "", model: "claude-sonnet-4-20250514", temperature: 0.7 },
        agent: {
          name: "AI Assistant",
          description: "",
          role: "general",
          tools: Object.fromEntries(TOOL_CATEGORIES.map((c) => [c.key, true])),
          systemPrompt: "",
        },
        notifications: { slackWebhook: "", emailEnabled: false, smtpHost: "", smtpPort: "587", telegramToken: "" },
      },
    };
  };

  const saved = loadSaved();
  const [currentStep, setCurrentStep] = useState(saved.step);
  const [admin, setAdmin] = useState<AdminForm>(saved.data.admin);
  const [llm, setLlm] = useState<LLMConfig>(saved.data.llm);
  const [agent, setAgent] = useState<AgentForm>(saved.data.agent);
  const [notifications, setNotifications] = useState<NotificationForm>(saved.data.notifications);
  const [workerTab, setWorkerTab] = useState<"docker" | "manual">("docker");
  const [showPassword, setShowPassword] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);

  // Persist state
  useEffect(() => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ step: currentStep, data: { admin, llm, agent, notifications } })
    );
  }, [currentStep, admin, llm, agent, notifications]);

  // System health check
  const { data: health } = useQuery<SystemHealth>({
    queryKey: ["setup-health"],
    queryFn: async () => {
      try {
        const res = await api.get("/settings/health");
        return res.data;
      } catch {
        return { database: true, redis: true, minio: true, mail: false };
      }
    },
  });

  // Workers polling
  const { data: workers } = useQuery<WorkerInfo[]>({
    queryKey: ["setup-workers"],
    queryFn: async () => {
      try {
        const res = await api.get("/workers/overview");
        return res.data;
      } catch {
        return DEMO_WORKERS;
      }
    },
    refetchInterval: currentStep === 3 ? 5000 : false,
  });

  const systemHealth = health ?? { database: true, redis: true, minio: true, mail: false };
  const workerList = workers ?? DEMO_WORKERS;

  // Validation
  const passwordStrength = getPasswordStrength(admin.password);
  const isStep2Valid =
    isValidEmail(admin.email) &&
    admin.fullName.trim().length > 0 &&
    admin.password.length >= 8 &&
    admin.password === admin.confirmPassword &&
    (passwordStrength.level === "fair" || passwordStrength.level === "good" || passwordStrength.level === "strong");

  const handleTestConnection = async () => {
    setTestingConnection(true);
    try {
      await api.post("/settings/test-llm", { provider: llm.provider, api_key: llm.apiKey, model: llm.model });
      toast.success("Connection successful!");
    } catch {
      toast.error("Connection failed. Check your API key and try again.");
    } finally {
      setTestingConnection(false);
    }
  };

  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  }, []);

  const handleApproveWorker = (name: string) => {
    toast.success(`Worker ${name} approved`);
  };

  const goNext = () => setCurrentStep((s) => Math.min(s + 1, STEPS.length - 1));
  const goBack = () => setCurrentStep((s) => Math.max(s - 1, 0));

  const handleFinish = () => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.setItem("whiteops_setup_complete", "true");
    navigate("/");
  };

  // Worker env content
  const workerEnv = `MASTER_URL=http://${window.location.hostname}:8000\nWORKER_NAME=worker-${Math.random().toString(36).slice(2, 8)}\n${llm.provider !== "ollama" ? `${llm.provider.toUpperCase()}_API_KEY=${llm.apiKey || "<your-api-key>"}` : "OLLAMA_HOST=http://localhost:11434"}`;

  // ─── Render Steps ────────────────────────────────────────────────────────

  const renderStep = () => {
    switch (currentStep) {
      // ── Step 1: Welcome ──────────────────────────────────────────────────
      case 0:
        return (
          <div className="space-y-8">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-neutral-900 dark:bg-white mb-4">
                <Rocket className="h-8 w-8 text-white dark:text-neutral-900" />
              </div>
              <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Welcome to White-Ops</h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2 max-w-md mx-auto">
                Let's get your AI workforce platform configured. This wizard will guide you through the initial setup in
                a few easy steps.
              </p>
            </div>

            <div className="card p-6 max-w-lg mx-auto dark:bg-neutral-800 dark:border-neutral-700">
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-4 flex items-center gap-2">
                <Monitor className="h-4 w-4" /> System Requirements Check
              </h3>
              <div className="space-y-3">
                {[
                  { label: "Database (PostgreSQL)", ok: systemHealth.database, icon: Database },
                  { label: "Redis", ok: systemHealth.redis, icon: HardDrive },
                  { label: "MinIO (Object Storage)", ok: systemHealth.minio, icon: HardDrive },
                  { label: "Mail Server (SMTP)", ok: systemHealth.mail, icon: Mail },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center justify-between p-3 rounded-lg bg-neutral-50 dark:bg-neutral-700/50"
                  >
                    <div className="flex items-center gap-3">
                      <item.icon className="h-4 w-4 text-neutral-400 dark:text-neutral-500" />
                      <span className="text-sm text-neutral-700 dark:text-neutral-300">{item.label}</span>
                    </div>
                    {item.ok ? (
                      <span className="flex items-center gap-1 text-green-600 dark:text-green-400 text-xs font-medium">
                        <CheckCircle2 className="h-4 w-4" /> Connected
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-red-500 dark:text-red-400 text-xs font-medium">
                        <X className="h-4 w-4" /> Unavailable
                      </span>
                    )}
                  </div>
                ))}
              </div>
              <p className="text-xs text-neutral-400 mt-4">
                Some services may not be available yet. You can continue setup and configure them later.
              </p>
            </div>

            {/* Prerequisites */}
            <div className="card p-6 max-w-lg mx-auto dark:bg-neutral-800 dark:border-neutral-700">
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-4 flex items-center gap-2">
                <Cpu className="h-4 w-4" /> Prerequisites
              </h3>

              {/* Minimum System Requirements */}
              <div className="mb-4">
                <p className="text-xs font-medium text-neutral-600 dark:text-neutral-300 mb-2">Minimum System Requirements</p>
                <div className="space-y-2">
                  {[
                    { label: "4 CPU cores (8+ recommended)", ok: true },
                    { label: "8 GB RAM (16+ recommended)", ok: true },
                    { label: "50 GB available disk space", ok: true },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center gap-2 text-xs text-neutral-700 dark:text-neutral-300">
                      {item.ok ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-green-500 flex-shrink-0" />
                      ) : (
                        <AlertTriangle className="h-3.5 w-3.5 text-amber-500 flex-shrink-0" />
                      )}
                      {item.label}
                    </div>
                  ))}
                </div>
              </div>

              {/* Required Software */}
              <div className="mb-4">
                <p className="text-xs font-medium text-neutral-600 dark:text-neutral-300 mb-2">Required Software</p>
                <div className="space-y-2">
                  {[
                    { label: "Docker Engine 24+", ok: true },
                    { label: "Docker Compose v2", ok: true },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center gap-2 text-xs text-neutral-700 dark:text-neutral-300">
                      {item.ok ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-green-500 flex-shrink-0" />
                      ) : (
                        <AlertTriangle className="h-3.5 w-3.5 text-amber-500 flex-shrink-0" />
                      )}
                      {item.label}
                    </div>
                  ))}
                </div>
              </div>

              {/* Network Requirements */}
              <div className="mb-4">
                <p className="text-xs font-medium text-neutral-600 dark:text-neutral-300 mb-2">Network Requirements</p>
                <div className="space-y-2">
                  {[
                    { label: "Port 8000 (API Server)", ok: true },
                    { label: "Port 3000 (Web UI)", ok: true },
                    { label: "Port 5432 (PostgreSQL)", ok: true },
                    { label: "Port 6379 (Redis)", ok: true },
                    { label: "Port 9000 (MinIO)", ok: true },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center gap-2 text-xs text-neutral-700 dark:text-neutral-300">
                      {item.ok ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-green-500 flex-shrink-0" />
                      ) : (
                        <AlertTriangle className="h-3.5 w-3.5 text-amber-500 flex-shrink-0" />
                      )}
                      {item.label}
                    </div>
                  ))}
                </div>
              </div>

              {/* Firewall Note */}
              <div className="flex gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-amber-800 dark:text-amber-300">
                  If deploying workers across multiple machines, ensure your firewall allows traffic on ports 8000, 6379, and 9000 between the master and worker nodes.
                </p>
              </div>
            </div>
          </div>
        );

      // ── Step 2: Admin Account ────────────────────────────────────────────
      case 1:
        return (
          <div className="max-w-lg mx-auto space-y-6">
            <div className="text-center mb-2">
              <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">Admin Account Setup</h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                Create the primary administrator account
              </p>
            </div>

            <div className="card p-6 space-y-4 dark:bg-neutral-800 dark:border-neutral-700">
              <div>
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1 block">
                  Email Address
                </label>
                <input
                  className="input w-full dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                  type="email"
                  placeholder="admin@company.com"
                  value={admin.email}
                  onChange={(e) => setAdmin({ ...admin, email: e.target.value })}
                />
                {admin.email && !isValidEmail(admin.email) && (
                  <p className="text-xs text-red-500 mt-1">Please enter a valid email address</p>
                )}
              </div>

              <div>
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1 block">
                  Full Name
                </label>
                <input
                  className="input w-full dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                  placeholder="John Admin"
                  value={admin.fullName}
                  onChange={(e) => setAdmin({ ...admin, fullName: e.target.value })}
                />
              </div>

              <div>
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1 block">
                  Password
                </label>
                <div className="relative">
                  <input
                    className="input w-full pr-10 dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                    type={showPassword ? "text" : "password"}
                    placeholder="Minimum 8 characters"
                    value={admin.password}
                    onChange={(e) => setAdmin({ ...admin, password: e.target.value })}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {admin.password && (
                  <div className="mt-2">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-neutral-200 dark:bg-neutral-600 rounded-full overflow-hidden">
                        <div
                          className={cn("h-full rounded-full transition-all", passwordStrength.color)}
                          style={{ width: `${(passwordStrength.score / 6) * 100}%` }}
                        />
                      </div>
                      <span
                        className={cn(
                          "text-xs font-medium capitalize",
                          passwordStrength.level === "weak"
                            ? "text-red-500"
                            : passwordStrength.level === "fair"
                              ? "text-amber-500"
                              : passwordStrength.level === "good"
                                ? "text-blue-500"
                                : "text-green-500"
                        )}
                      >
                        {passwordStrength.level}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <div>
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1 block">
                  Confirm Password
                </label>
                <input
                  className="input w-full dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                  type="password"
                  placeholder="Re-enter your password"
                  value={admin.confirmPassword}
                  onChange={(e) => setAdmin({ ...admin, confirmPassword: e.target.value })}
                />
                {admin.confirmPassword && admin.password !== admin.confirmPassword && (
                  <p className="text-xs text-red-500 mt-1">Passwords do not match</p>
                )}
              </div>
            </div>
          </div>
        );

      // ── Step 3: LLM Config ──────────────────────────────────────────────
      case 2:
        return (
          <div className="max-w-lg mx-auto space-y-6">
            <div className="text-center mb-2">
              <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">LLM Provider Configuration</h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                Connect your preferred language model provider
              </p>
            </div>

            <div className="card p-6 space-y-5 dark:bg-neutral-800 dark:border-neutral-700">
              {/* Provider selection */}
              <div className="space-y-2">
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 block">Provider</label>
                <div className="grid grid-cols-2 gap-2">
                  {(Object.keys(PROVIDER_INFO) as LLMProvider[]).map((key) => (
                    <button
                      key={key}
                      onClick={() =>
                        setLlm({ ...llm, provider: key, model: MODEL_OPTIONS[key][0] ?? "" })
                      }
                      className={cn(
                        "relative flex items-center gap-2 p-3 rounded-lg border text-left text-sm font-medium transition-colors",
                        llm.provider === key
                          ? "border-neutral-900 bg-neutral-900 text-white dark:border-white dark:bg-white dark:text-neutral-900"
                          : "border-neutral-200 text-neutral-700 hover:border-neutral-400 dark:border-neutral-600 dark:text-neutral-300 dark:hover:border-neutral-500"
                      )}
                    >
                      <Brain className="h-4 w-4 flex-shrink-0" />
                      <span>{PROVIDER_INFO[key].name}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* API Key */}
              <div>
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1 block">
                  {llm.provider === "ollama" ? "Ollama Host URL" : "API Key"}
                </label>
                <div className="relative">
                  <input
                    className="input w-full pr-10 dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                    type={showApiKey ? "text" : "password"}
                    placeholder={llm.provider === "ollama" ? "http://localhost:11434" : "sk-..."}
                    value={llm.apiKey}
                    onChange={(e) => setLlm({ ...llm, apiKey: e.target.value })}
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                  >
                    {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Model selection */}
              <div>
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1 block">Model</label>
                <select
                  className="input w-full dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                  value={llm.model}
                  onChange={(e) => setLlm({ ...llm, model: e.target.value })}
                >
                  {MODEL_OPTIONS[llm.provider].map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>

              {/* Temperature */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300">Temperature</label>
                  <span className="text-xs text-neutral-500 font-mono">{llm.temperature.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={llm.temperature}
                  onChange={(e) => setLlm({ ...llm, temperature: parseFloat(e.target.value) })}
                  className="w-full accent-neutral-900 dark:accent-white"
                />
                <div className="flex justify-between text-[10px] text-neutral-400 mt-0.5">
                  <span>Precise</span>
                  <span>Creative</span>
                </div>
              </div>

              {/* Test button */}
              <button
                onClick={handleTestConnection}
                disabled={testingConnection || (!llm.apiKey && llm.provider !== "ollama")}
                className="btn-primary text-sm w-full flex items-center justify-center gap-2"
              >
                {testingConnection ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Zap className="h-4 w-4" />
                )}
                Test Connection
              </button>
            </div>
          </div>
        );

      // ── Step 4: Workers ──────────────────────────────────────────────────
      case 3:
        return (
          <div className="max-w-3xl mx-auto space-y-6">
            <div className="text-center mb-2">
              <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">Worker Deployment</h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                Deploy worker nodes to run your AI agents
              </p>
            </div>

            {/* Tabs */}
            <div className="card dark:bg-neutral-800 dark:border-neutral-700 overflow-hidden">
              <div className="flex border-b border-neutral-200 dark:border-neutral-700">
                {(["docker", "manual"] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setWorkerTab(tab)}
                    className={cn(
                      "flex-1 px-4 py-3 text-sm font-medium border-b-2 transition-colors -mb-px",
                      workerTab === tab
                        ? "border-neutral-900 text-neutral-900 dark:border-white dark:text-white"
                        : "border-transparent text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                    )}
                  >
                    {tab === "docker" ? "Docker (Recommended)" : "Manual"}
                  </button>
                ))}
              </div>

              <div className="p-6">
                {workerTab === "docker" ? (
                  <div className="space-y-6">
                    {/* Prerequisites box */}
                    <div className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 p-4">
                      <h4 className="text-xs font-semibold text-blue-900 dark:text-blue-300 mb-2 flex items-center gap-1.5">
                        <Info className="h-3.5 w-3.5" /> Prerequisites
                      </h4>
                      <ul className="space-y-1.5 text-xs text-blue-800 dark:text-blue-300">
                        <li className="flex items-center gap-2"><CheckCircle2 className="h-3 w-3 flex-shrink-0" /> Docker Engine 24+ and Docker Compose v2 required</li>
                        <li className="flex items-center gap-2"><CheckCircle2 className="h-3 w-3 flex-shrink-0" /> Minimum 2 CPU cores, 4 GB RAM per worker node</li>
                        <li className="flex items-center gap-2"><CheckCircle2 className="h-3 w-3 flex-shrink-0" /> Network access to master server on port 8000</li>
                      </ul>
                    </div>

                    {/* Quick start command */}
                    <div>
                      <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
                        Quick start -- add to your docker-compose.yml or run:
                      </p>
                      <div className="relative">
                        <pre className="bg-neutral-900 dark:bg-neutral-950 text-green-400 rounded-lg p-4 text-xs font-mono overflow-x-auto">
{`# Add to your docker-compose.yml or run separately:
docker compose up worker --scale worker=3`}
                        </pre>
                        <button
                          onClick={() =>
                            copyToClipboard("docker compose up worker --scale worker=3")
                          }
                          className="absolute top-2 right-2 p-1.5 rounded bg-neutral-700 hover:bg-neutral-600 text-neutral-400 hover:text-neutral-200 transition-colors"
                          title="Copy"
                        >
                          <Copy className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Step-by-step guide */}
                    <div>
                      <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-3">Step-by-Step Guide</h4>
                      <div className="space-y-4">
                        {/* Step 1 */}
                        <div className="flex gap-3">
                          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-bold flex items-center justify-center">1</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 mb-2">
                              Copy environment variables to <code className="text-xs bg-neutral-100 dark:bg-neutral-700 px-1.5 py-0.5 rounded">.env</code> file
                            </p>
                            <div className="relative">
                              <pre className="bg-neutral-900 dark:bg-neutral-950 text-green-400 rounded-lg p-4 text-xs font-mono overflow-x-auto whitespace-pre">
{workerEnv}
                              </pre>
                              <button
                                onClick={() => copyToClipboard(workerEnv)}
                                className="absolute top-2 right-2 p-1.5 rounded bg-neutral-700 hover:bg-neutral-600 text-neutral-400 hover:text-neutral-200 transition-colors"
                                title="Copy"
                              >
                                <Copy className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </div>
                        </div>
                        {/* Step 2 */}
                        <div className="flex gap-3">
                          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-bold flex items-center justify-center">2</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 mb-1">Start the worker</p>
                            <code className="text-xs bg-neutral-100 dark:bg-neutral-700 px-2 py-1 rounded block font-mono text-neutral-700 dark:text-neutral-300">docker compose up worker -d</code>
                          </div>
                        </div>
                        {/* Step 3 */}
                        <div className="flex gap-3">
                          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-bold flex items-center justify-center">3</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 mb-1">Scale to multiple workers</p>
                            <code className="text-xs bg-neutral-100 dark:bg-neutral-700 px-2 py-1 rounded block font-mono text-neutral-700 dark:text-neutral-300">docker compose up worker --scale worker=N -d</code>
                          </div>
                        </div>
                        {/* Step 4 */}
                        <div className="flex gap-3">
                          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-bold flex items-center justify-center">4</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">Verify connection in the worker table below</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Multiple PC Deployment */}
                    <div className="rounded-lg border border-neutral-200 dark:border-neutral-600 bg-neutral-50 dark:bg-neutral-700/30 p-4">
                      <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-3 flex items-center gap-2">
                        <Globe className="h-4 w-4" /> Multiple PC Deployment
                      </h4>
                      <p className="text-xs text-neutral-600 dark:text-neutral-400 mb-3">
                        To deploy workers on remote machines, follow these steps on each target machine:
                      </p>
                      <ol className="space-y-3 text-xs text-neutral-700 dark:text-neutral-300">
                        <li className="flex gap-2">
                          <span className="font-bold text-neutral-500 flex-shrink-0">1.</span>
                          <div>Install Docker: <code className="bg-neutral-200 dark:bg-neutral-600 px-1.5 py-0.5 rounded font-mono">curl -fsSL https://get.docker.com | sh</code></div>
                        </li>
                        <li className="flex gap-2">
                          <span className="font-bold text-neutral-500 flex-shrink-0">2.</span>
                          <span>Clone the worker config -- create <code className="bg-neutral-200 dark:bg-neutral-600 px-1.5 py-0.5 rounded font-mono">docker-compose.worker.yml</code> with the content below</span>
                        </li>
                        <li className="flex gap-2">
                          <span className="font-bold text-neutral-500 flex-shrink-0">3.</span>
                          <span>Create <code className="bg-neutral-200 dark:bg-neutral-600 px-1.5 py-0.5 rounded font-mono">.env</code> with MASTER_URL pointing to this server's IP</span>
                        </li>
                        <li className="flex gap-2">
                          <span className="font-bold text-neutral-500 flex-shrink-0">4.</span>
                          <div>Run: <code className="bg-neutral-200 dark:bg-neutral-600 px-1.5 py-0.5 rounded font-mono">docker compose -f docker-compose.worker.yml up -d</code></div>
                        </li>
                      </ol>
                      <div className="relative mt-3">
                        <pre className="bg-neutral-900 dark:bg-neutral-950 text-green-400 rounded-lg p-4 text-xs font-mono overflow-x-auto whitespace-pre">
{`# docker-compose.worker.yml
services:
  worker:
    image: ghcr.io/your-org/whiteops-worker:latest
    environment:
      - MASTER_URL=http://${window.location.hostname}:8000
      - WORKER_NAME=worker-\${HOSTNAME}
      - ${llm.provider !== "ollama" ? `${llm.provider.toUpperCase()}_API_KEY=\${${llm.provider.toUpperCase()}_API_KEY}` : "OLLAMA_HOST=http://localhost:11434"}
      - REDIS_HOST=${window.location.hostname}
      - REDIS_PASSWORD=\${REDIS_PASSWORD}
    restart: unless-stopped`}
                        </pre>
                        <button
                          onClick={() => copyToClipboard(`# docker-compose.worker.yml
services:
  worker:
    image: ghcr.io/your-org/whiteops-worker:latest
    environment:
      - MASTER_URL=http://${window.location.hostname}:8000
      - WORKER_NAME=worker-\${HOSTNAME}
      - ${llm.provider !== "ollama" ? `${llm.provider.toUpperCase()}_API_KEY=\${${llm.provider.toUpperCase()}_API_KEY}` : "OLLAMA_HOST=http://localhost:11434"}
      - REDIS_HOST=${window.location.hostname}
      - REDIS_PASSWORD=\${REDIS_PASSWORD}
    restart: unless-stopped`)}
                          className="absolute top-2 right-2 p-1.5 rounded bg-neutral-700 hover:bg-neutral-600 text-neutral-400 hover:text-neutral-200 transition-colors"
                          title="Copy"
                        >
                          <Copy className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Firewall Rules */}
                    <div className="flex gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                      <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                      <div className="text-xs text-amber-800 dark:text-amber-300">
                        <p className="font-semibold mb-1">Firewall Rules</p>
                        <p className="mb-1">If deploying across machines, ensure these ports are open between master and worker nodes:</p>
                        <ul className="space-y-0.5 ml-2">
                          <li>Port <strong>8000</strong> -- API Server</li>
                          <li>Port <strong>6379</strong> -- Redis</li>
                          <li>Port <strong>9000</strong> -- MinIO (Object Storage)</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Manual deployment comprehensive guide */}
                    <div className="space-y-5">
                      {/* Step 1: System Requirements */}
                      <div className="flex gap-3">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-bold flex items-center justify-center">1</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 mb-2">System Requirements</p>
                          <div className="space-y-1 text-xs text-neutral-600 dark:text-neutral-400 dark:text-neutral-500">
                            <p>Python 3.12+, pip, git, and Playwright browsers are required.</p>
                          </div>
                        </div>
                      </div>

                      {/* Step 2: Clone & Install */}
                      <div className="flex gap-3">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-bold flex items-center justify-center">2</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 mb-2">Clone & Install</p>
                          <div className="relative">
                            <pre className="bg-neutral-900 dark:bg-neutral-950 text-green-400 rounded-lg p-4 text-xs font-mono overflow-x-auto whitespace-pre">
{`git clone https://github.com/your-org/whiteops.git
cd whiteops/worker
pip install -e .
playwright install chromium`}
                            </pre>
                            <button
                              onClick={() => copyToClipboard(`git clone https://github.com/your-org/whiteops.git\ncd whiteops/worker\npip install -e .\nplaywright install chromium`)}
                              className="absolute top-2 right-2 p-1.5 rounded bg-neutral-700 hover:bg-neutral-600 text-neutral-400 hover:text-neutral-200 transition-colors"
                              title="Copy"
                            >
                              <Copy className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Step 3: Configure Environment */}
                      <div className="flex gap-3">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-bold flex items-center justify-center">3</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 mb-2">Configure Environment</p>
                          <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-2">
                            Create a <code className="bg-neutral-100 dark:bg-neutral-700 px-1 py-0.5 rounded">.env</code> file in the worker directory:
                          </p>
                          <div className="relative">
                            <pre className="bg-neutral-900 dark:bg-neutral-950 text-green-400 rounded-lg p-4 text-xs font-mono overflow-x-auto whitespace-pre">
{workerEnv}
                            </pre>
                            <button
                              onClick={() => copyToClipboard(workerEnv)}
                              className="absolute top-2 right-2 p-1.5 rounded bg-neutral-700 hover:bg-neutral-600 text-neutral-400 hover:text-neutral-200 transition-colors"
                              title="Copy"
                            >
                              <Copy className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Step 4: Start Worker */}
                      <div className="flex gap-3">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-bold flex items-center justify-center">4</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 mb-1">Start Worker</p>
                          <code className="text-xs bg-neutral-100 dark:bg-neutral-700 px-2 py-1 rounded block font-mono text-neutral-700 dark:text-neutral-300">python -m agent.main</code>
                        </div>
                      </div>

                      {/* Step 5: Verify */}
                      <div className="flex gap-3">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-bold flex items-center justify-center">5</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 mb-1">Verify</p>
                          <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">
                            Check the worker table below -- it should appear within 30 seconds.
                          </p>
                        </div>
                      </div>

                      {/* Step 6: Run as Service */}
                      <div className="flex gap-3">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-bold flex items-center justify-center">6</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 mb-2">Run as Service (Production)</p>
                          <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-2">
                            For production Linux deployments, create a systemd service:
                          </p>
                          <div className="relative">
                            <pre className="bg-neutral-900 dark:bg-neutral-950 text-green-400 rounded-lg p-4 text-xs font-mono overflow-x-auto whitespace-pre">
{`[Unit]
Description=WhiteOps Worker Agent
After=network.target

[Service]
Type=simple
User=whiteops
WorkingDirectory=/opt/whiteops/worker
ExecStart=/opt/whiteops/worker/venv/bin/python -m agent.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target`}
                            </pre>
                            <button
                              onClick={() => copyToClipboard(`[Unit]
Description=WhiteOps Worker Agent
After=network.target

[Service]
Type=simple
User=whiteops
WorkingDirectory=/opt/whiteops/worker
ExecStart=/opt/whiteops/worker/venv/bin/python -m agent.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target`)}
                              className="absolute top-2 right-2 p-1.5 rounded bg-neutral-700 hover:bg-neutral-600 text-neutral-400 hover:text-neutral-200 transition-colors"
                              title="Copy"
                            >
                              <Copy className="h-3.5 w-3.5" />
                            </button>
                          </div>
                          <p className="text-xs text-neutral-400 mt-2">
                            Save as <code className="bg-neutral-100 dark:bg-neutral-700 px-1 py-0.5 rounded">/etc/systemd/system/whiteops-worker.service</code>, then run{" "}
                            <code className="bg-neutral-100 dark:bg-neutral-700 px-1 py-0.5 rounded">sudo systemctl enable --now whiteops-worker</code>
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Connected Workers */}
            <div className="card dark:bg-neutral-800 dark:border-neutral-700 overflow-hidden">
              <div className="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
                    <Server className="h-4 w-4" /> Connected Workers
                  </h3>
                  {workerList.length > 0 && (
                    <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300">
                      {workerList.filter((w) => w.status === "online").length} connected, {workerList.filter((w) => w.status === "pending").length} pending
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toast.success("Refreshing worker list...")}
                    className="flex items-center gap-1 text-xs font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors px-2 py-1 rounded border border-neutral-200 dark:border-neutral-600"
                  >
                    <RefreshCw className="h-3 w-3" /> Refresh Now
                  </button>
                  <div className="flex items-center gap-1 text-xs text-neutral-400 dark:text-neutral-500">
                    <RefreshCw className="h-3 w-3 animate-spin" /> Polling every 5s
                  </div>
                </div>
              </div>
              {workerList.length === 0 ? (
                <div className="p-8 text-center">
                  <Server className="h-8 w-8 text-neutral-300 dark:text-neutral-600 mx-auto mb-2" />
                  <p className="text-sm text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">Waiting for workers to connect...</p>
                  <p className="text-xs text-neutral-400 mt-1">Deploy a worker using the instructions above</p>
                </div>
              ) : (
                <table className="w-full">
                  <thead>
                    <tr>
                      <th className="table-header">Worker Name</th>
                      <th className="table-header">IP</th>
                      <th className="table-header text-center">Status</th>
                      <th className="table-header text-center">CPU %</th>
                      <th className="table-header text-center">Memory %</th>
                      <th className="table-header text-center">Agents</th>
                      <th className="table-header text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {workerList.map((w) => (
                      <tr key={w.name} className="border-b border-neutral-100 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700/50">
                        <td className="px-4 py-3 text-xs font-medium text-neutral-900 dark:text-neutral-100 font-mono">
                          {w.name}
                        </td>
                        <td className="px-4 py-3 text-xs text-neutral-500 font-mono">{w.ip}</td>
                        <td className="px-4 py-3 text-center">
                          <span
                            className={cn(
                              "inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full",
                              w.status === "online"
                                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                : w.status === "pending"
                                  ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                                  : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                            )}
                          >
                            <span
                              className={cn(
                                "w-1.5 h-1.5 rounded-full",
                                w.status === "online"
                                  ? "bg-green-500"
                                  : w.status === "pending"
                                    ? "bg-amber-500"
                                    : "bg-red-500"
                              )}
                            />
                            {w.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-neutral-600 dark:text-neutral-400 text-center">
                          {w.cpu}%
                        </td>
                        <td className="px-4 py-3 text-xs text-neutral-600 dark:text-neutral-400 text-center">
                          {w.memory}%
                        </td>
                        <td className="px-4 py-3 text-xs text-neutral-600 dark:text-neutral-400 text-center">
                          {w.agents}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {w.status === "online" && (
                              <button
                                onClick={() => toast.success(`Testing connection to ${w.name}...`)}
                                className="text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1"
                              >
                                <Play className="h-3 w-3" /> Test
                              </button>
                            )}
                            {w.status === "pending" && (
                              <div className="flex items-center gap-2">
                                <div className="group relative">
                                  <Info className="h-3.5 w-3.5 text-neutral-400 cursor-help" />
                                  <div className="absolute bottom-full right-0 mb-1 w-48 p-2 bg-neutral-900 dark:bg-neutral-700 text-white text-[10px] rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                                    This worker has connected but needs admin approval before it can run agents.
                                  </div>
                                </div>
                                <button
                                  onClick={() => handleApproveWorker(w.name)}
                                  className="text-xs font-medium text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300"
                                >
                                  Approve
                                </button>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        );

      // ── Step 5: First Agent ──────────────────────────────────────────────
      case 4:
        return (
          <div className="max-w-lg mx-auto space-y-6">
            <div className="text-center mb-2">
              <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">Create Your First Agent</h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                Configure an AI agent to start automating tasks
              </p>
            </div>

            <div className="card p-6 space-y-4 dark:bg-neutral-800 dark:border-neutral-700">
              <div>
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1 block">
                  Agent Name
                </label>
                <input
                  className="input w-full dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                  placeholder="AI Assistant"
                  value={agent.name}
                  onChange={(e) => setAgent({ ...agent, name: e.target.value })}
                />
              </div>

              <div>
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1 block">
                  Description
                </label>
                <input
                  className="input w-full dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                  placeholder="A general-purpose AI assistant for your team"
                  value={agent.description}
                  onChange={(e) => setAgent({ ...agent, description: e.target.value })}
                />
              </div>

              <div>
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1 block">Role</label>
                <select
                  className="input w-full dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                  value={agent.role}
                  onChange={(e) => setAgent({ ...agent, role: e.target.value })}
                >
                  <option value="general">General Assistant</option>
                  <option value="developer">Developer</option>
                  <option value="analyst">Analyst</option>
                  <option value="researcher">Researcher</option>
                  <option value="writer">Writer</option>
                </select>
              </div>

              {/* Tool categories */}
              <div>
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-2 block">
                  Tool Categories
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {TOOL_CATEGORIES.map((cat) => (
                    <label
                      key={cat.key}
                      className={cn(
                        "flex items-center gap-2.5 p-2.5 rounded-lg border cursor-pointer transition-colors",
                        agent.tools[cat.key]
                          ? "border-neutral-900 bg-neutral-50 dark:border-white dark:bg-neutral-700/50"
                          : "border-neutral-200 dark:border-neutral-600 hover:border-neutral-300 dark:hover:border-neutral-500"
                      )}
                    >
                      <input
                        type="checkbox"
                        className="sr-only"
                        checked={agent.tools[cat.key] ?? true}
                        onChange={(e) =>
                          setAgent({ ...agent, tools: { ...agent.tools, [cat.key]: e.target.checked } })
                        }
                      />
                      <div
                        className={cn(
                          "w-4 h-4 rounded border flex items-center justify-center flex-shrink-0",
                          agent.tools[cat.key]
                            ? "bg-neutral-900 border-neutral-900 dark:bg-white dark:border-white"
                            : "border-neutral-300 dark:border-neutral-500"
                        )}
                      >
                        {agent.tools[cat.key] && (
                          <Check className="h-3 w-3 text-white dark:text-neutral-900" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <cat.icon className="h-3.5 w-3.5 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />
                          <span className="text-xs font-medium text-neutral-800 dark:text-neutral-200">
                            {cat.label}
                          </span>
                        </div>
                        <p className="text-[10px] text-neutral-400 mt-0.5 truncate">{cat.items.join(", ")}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1 block">
                  System Prompt
                </label>
                <textarea
                  className="input w-full h-24 resize-none dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                  placeholder="You are a professional AI assistant..."
                  value={agent.systemPrompt}
                  onChange={(e) => setAgent({ ...agent, systemPrompt: e.target.value })}
                />
              </div>
            </div>
          </div>
        );

      // ── Step 6: Notifications ────────────────────────────────────────────
      case 5:
        return (
          <div className="max-w-lg mx-auto space-y-6">
            <div className="text-center mb-2">
              <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">Stay Informed</h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                Configure notifications to stay on top of your AI workforce (optional)
              </p>
            </div>

            <div className="card p-6 space-y-5 dark:bg-neutral-800 dark:border-neutral-700">
              {/* Slack */}
              <div>
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1 flex items-center gap-2">
                  <Globe className="h-3.5 w-3.5" /> Slack Webhook URL
                </label>
                <input
                  className="input w-full dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                  placeholder="https://hooks.slack.com/services/..."
                  value={notifications.slackWebhook}
                  onChange={(e) => setNotifications({ ...notifications, slackWebhook: e.target.value })}
                />
              </div>

              {/* Email */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 flex items-center gap-2">
                    <Mail className="h-3.5 w-3.5" /> Email Notifications
                  </label>
                  <button
                    onClick={() =>
                      setNotifications({ ...notifications, emailEnabled: !notifications.emailEnabled })
                    }
                    className={cn(
                      "w-10 h-5 rounded-full transition-colors relative",
                      notifications.emailEnabled ? "bg-green-500" : "bg-neutral-300 dark:bg-neutral-600"
                    )}
                  >
                    <span
                      className={cn(
                        "absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform",
                        notifications.emailEnabled ? "translate-x-5" : "translate-x-0.5"
                      )}
                    />
                  </button>
                </div>
                {notifications.emailEnabled && (
                  <div className="grid grid-cols-3 gap-2 mt-2">
                    <input
                      className="input col-span-2 dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                      placeholder="SMTP Host"
                      value={notifications.smtpHost}
                      onChange={(e) => setNotifications({ ...notifications, smtpHost: e.target.value })}
                    />
                    <input
                      className="input dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                      placeholder="Port"
                      value={notifications.smtpPort}
                      onChange={(e) => setNotifications({ ...notifications, smtpPort: e.target.value })}
                    />
                  </div>
                )}
              </div>

              {/* Telegram */}
              <div>
                <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1 flex items-center gap-2">
                  <MessageSquare className="h-3.5 w-3.5" /> Telegram Bot Token
                </label>
                <input
                  className="input w-full dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-100"
                  placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                  value={notifications.telegramToken}
                  onChange={(e) => setNotifications({ ...notifications, telegramToken: e.target.value })}
                />
              </div>
            </div>
          </div>
        );

      // ── Step 7: Complete ─────────────────────────────────────────────────
      case 6:
        return (
          <div className="max-w-lg mx-auto space-y-6">
            <div className="text-center mb-2">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 mb-4">
                <CheckCircle2 className="h-8 w-8 text-green-600 dark:text-green-400" />
              </div>
              <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Setup Complete!</h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                Your White-Ops platform is ready to go
              </p>
            </div>

            {/* Summary cards */}
            <div className="grid grid-cols-2 gap-3">
              {[
                {
                  icon: Shield,
                  label: "Admin Account",
                  value: admin.fullName || "Configured",
                  color: "text-blue-600 dark:text-blue-400",
                  bg: "bg-blue-50 dark:bg-blue-900/20",
                },
                {
                  icon: Brain,
                  label: "LLM Provider",
                  value: PROVIDER_INFO[llm.provider].name,
                  color: "text-purple-600 dark:text-purple-400",
                  bg: "bg-purple-50 dark:bg-purple-900/20",
                },
                {
                  icon: Server,
                  label: "Workers Connected",
                  value: `${workerList.filter((w) => w.status === "online").length} online`,
                  color: "text-green-600 dark:text-green-400",
                  bg: "bg-green-50 dark:bg-green-900/20",
                },
                {
                  icon: Bot,
                  label: "Agent Created",
                  value: agent.name || "AI Assistant",
                  color: "text-amber-600 dark:text-amber-400",
                  bg: "bg-amber-50 dark:bg-amber-900/20",
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className={cn("card p-4 dark:bg-neutral-800 dark:border-neutral-700", item.bg)}
                >
                  <item.icon className={cn("h-5 w-5 mb-2", item.color)} />
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{item.label}</p>
                  <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mt-0.5">
                    {item.value}
                  </p>
                </div>
              ))}
            </div>

            {/* Quick actions */}
            <div className="space-y-2">
              <button
                onClick={handleFinish}
                className="btn-primary text-sm w-full flex items-center justify-center gap-2 py-3"
              >
                <Rocket className="h-4 w-4" /> Go to Dashboard
              </button>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => {
                    localStorage.removeItem(STORAGE_KEY);
                    navigate("/tasks");
                  }}
                  className="btn-secondary text-sm flex items-center justify-center gap-2 py-2.5 dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-200 dark:hover:bg-neutral-600"
                >
                  <Zap className="h-4 w-4" /> Create a Task
                </button>
                <button
                  onClick={() => {
                    localStorage.removeItem(STORAGE_KEY);
                    navigate("/workers");
                  }}
                  className="btn-secondary text-sm flex items-center justify-center gap-2 py-2.5 dark:bg-neutral-700 dark:border-neutral-600 dark:text-neutral-200 dark:hover:bg-neutral-600"
                >
                  <Server className="h-4 w-4" /> Add More Workers
                </button>
              </div>
            </div>

            {/* What's Next */}
            <div className="card p-6 dark:bg-neutral-800 dark:border-neutral-700">
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-4 flex items-center gap-2">
                <BookOpen className="h-4 w-4" /> What's Next
              </h3>
              <div className="space-y-3">
                {[
                  { label: "Create your first task from the Dashboard", icon: Zap, href: "/tasks" },
                  { label: "Explore the 70+ tools available to your agents", icon: Terminal, href: "/tools" },
                  { label: "Set up approval workflows for sensitive operations", icon: Shield, href: "/settings/workflows" },
                  { label: "Configure cost budgets and alerts", icon: DollarSign, href: "/settings/billing" },
                  { label: "Review security settings (MFA, IP whitelists)", icon: Lock, href: "/settings/security" },
                  { label: "Check out the API documentation at /docs", icon: FileCode, href: "/docs" },
                ].map((item) => (
                  <button
                    key={item.label}
                    onClick={() => {
                      localStorage.removeItem(STORAGE_KEY);
                      navigate(item.href);
                    }}
                    className="w-full flex items-center gap-3 p-3 rounded-lg text-left hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors group"
                  >
                    <div className="w-5 h-5 rounded border border-neutral-300 dark:border-neutral-600 flex items-center justify-center flex-shrink-0 group-hover:border-neutral-400 dark:group-hover:border-neutral-500">
                      <span className="w-2.5 h-2.5 rounded-sm" />
                    </div>
                    <item.icon className="h-4 w-4 text-neutral-400 flex-shrink-0" />
                    <span className="text-sm text-neutral-700 dark:text-neutral-300 group-hover:text-neutral-900 dark:group-hover:text-neutral-100 transition-colors flex-1">
                      {item.label}
                    </span>
                    <ExternalLink className="h-3.5 w-3.5 text-neutral-300 dark:text-neutral-600 group-hover:text-neutral-400 dark:group-hover:text-neutral-500 transition-colors" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  // ─── Main Render ─────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900">
      {/* Step indicator */}
      <div className="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 px-6 py-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center justify-between mb-3">
            {STEPS.map((step, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="flex flex-col items-center">
                  <button
                    onClick={() => i < currentStep && setCurrentStep(i)}
                    disabled={i > currentStep}
                    className={cn(
                      "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors",
                      i < currentStep
                        ? "bg-green-500 text-white cursor-pointer"
                        : i === currentStep
                          ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
                          : "bg-neutral-200 text-neutral-400 dark:bg-neutral-700 dark:text-neutral-500 cursor-not-allowed"
                    )}
                  >
                    {i < currentStep ? <Check className="h-4 w-4" /> : i + 1}
                  </button>
                  <span className={cn(
                    "hidden sm:block text-[10px] mt-1",
                    i === currentStep
                      ? "text-neutral-900 dark:text-neutral-100 font-medium"
                      : "text-neutral-400 dark:text-neutral-500 dark:text-neutral-400 dark:text-neutral-500"
                  )}>
                    {step.label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={cn(
                      "w-8 lg:w-16 h-0.5 mx-1",
                      i < currentStep
                        ? "bg-green-500"
                        : "bg-neutral-200 dark:bg-neutral-700"
                    )}
                  />
                )}
              </div>
            ))}
          </div>
          {/* Progress bar */}
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-neutral-900 dark:bg-white rounded-full transition-all duration-500"
                style={{ width: `${(currentStep / (STEPS.length - 1)) * 100}%` }}
              />
            </div>
            <span className="text-xs text-neutral-400 ml-2">{Math.round((currentStep / (STEPS.length - 1)) * 100)}%</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-3xl mx-auto px-6 py-8 pb-28">{renderStep()}</div>

      {/* Footer navigation */}
      {currentStep < STEPS.length - 1 && (
        <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-neutral-800 border-t border-neutral-200 dark:border-neutral-700 px-6 py-4">
          <div className="max-w-3xl mx-auto flex items-center justify-between">
            <button
              onClick={goBack}
              disabled={currentStep === 0}
              className={cn(
                "flex items-center gap-1.5 text-sm font-medium transition-colors",
                currentStep === 0
                  ? "text-neutral-300 dark:text-neutral-600 cursor-not-allowed"
                  : "text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100"
              )}
            >
              <ChevronLeft className="h-4 w-4" /> Back
            </button>

            <div className="flex items-center gap-3">
              {currentStep === 5 && (
                <button
                  onClick={goNext}
                  className="text-sm font-medium text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                >
                  Skip
                </button>
              )}
              <button
                onClick={goNext}
                disabled={currentStep === 1 && !isStep2Valid}
                className={cn(
                  "btn-primary text-sm flex items-center gap-1.5",
                  currentStep === 1 && !isStep2Valid && "opacity-50 cursor-not-allowed"
                )}
              >
                Continue <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
