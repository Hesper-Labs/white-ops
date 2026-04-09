import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Settings as SettingsIcon, Settings2, Key, Mail, Shield, Bell, HardDrive,
  CheckCircle, XCircle, Save, Globe, Eye, EyeOff,
  TestTube2, Plug, Database, ToggleLeft, AlertTriangle, Trash2,
  Link2, Clock, Download, Star,
} from "lucide-react";
import { settingsApi } from "../api/endpoints";
import { useThemeStore } from "../stores/themeStore";
import toast from "react-hot-toast";

// ---- Tab definitions (inline) ----

const TABS = [
  { id: "general", label: "General", icon: Settings2 },
  { id: "llm", label: "LLM Providers", icon: Key },
  { id: "email", label: "Email", icon: Mail },
  { id: "storage", label: "Storage", icon: HardDrive },
  { id: "security", label: "Security", icon: Shield },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "integrations", label: "Integrations", icon: Plug },
  { id: "backups", label: "Backups", icon: Database },
  { id: "features", label: "Feature Flags", icon: ToggleLeft },
  { id: "danger", label: "Danger Zone", icon: AlertTriangle },
] as const;

// ---- Helpers ----

function SectionCard({ title, icon: Icon, children }: { title: string; icon: React.ElementType; children: React.ReactNode }) {
  return (
    <div className="card p-6 mb-6">
      <div className="flex items-center gap-3 mb-5">
        <Icon className="h-5 w-5 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />
        <h3 className="text-base font-semibold">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function Toggle({ checked, onChange, label, description }: { checked: boolean; onChange: (v: boolean) => void; label: string; description?: string }) {
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <p className="text-sm font-medium">{label}</p>
        {description && <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{description}</p>}
      </div>
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
          checked ? "bg-neutral-900 dark:bg-white" : "bg-neutral-300 dark:bg-neutral-600"
        }`}
      >
        <span
          className={`inline-block h-3.5 w-3.5 rounded-full bg-white dark:bg-neutral-900 transition-transform ${
            checked ? "translate-x-4.5" : "translate-x-0.5"
          }`}
        />
      </button>
    </div>
  );
}

function PasswordInput({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input
        type={show ? "text" : "password"}
        className="input pr-10 w-full"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder || "Enter API key..."}
      />
      <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600" onClick={() => setShow(!show)}>
        {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
}

function SaveButton({ onClick, loading, disabled }: { onClick: () => void; loading?: boolean; disabled?: boolean }) {
  return (
    <div className="flex justify-end pt-4 border-t border-neutral-200 dark:border-neutral-700 mt-6">
      <button
        className="btn-primary flex items-center gap-2"
        onClick={onClick}
        disabled={disabled || loading}
      >
        <Save className="h-4 w-4" />
        {loading ? "Saving..." : "Save Changes"}
      </button>
    </div>
  );
}

// ---- Tab Content Components ----

function GeneralTab() {
  const { theme, setTheme } = useThemeStore();
  const [language, setLanguage] = useState("en");
  const [timezone, setTimezone] = useState("UTC");

  const handleSave = () => toast.success("General settings saved");

  return (
    <SectionCard title="General Settings" icon={Globe}>
      <div className="space-y-4 max-w-lg">
        <div>
          <label className="block text-sm font-medium mb-1">Application Name</label>
          <input className="input w-full bg-neutral-50 dark:bg-neutral-700 cursor-not-allowed" value="White-Ops" readOnly />
          <p className="text-xs text-neutral-400 mt-1">Application name cannot be changed</p>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Environment</label>
          <span className="inline-block px-2.5 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
            PRODUCTION
          </span>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Default Language</label>
          <select className="input w-48" value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="en">English</option>
            <option value="tr">Turkish</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Theme</label>
          <select
            className="input w-48"
            value={theme}
            onChange={(e) => setTheme(e.target.value as "light" | "dark" | "system")}
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Timezone</label>
          <select className="input w-64" value={timezone} onChange={(e) => setTimezone(e.target.value)}>
            <option value="UTC">UTC</option>
            <option value="America/New_York">America/New_York (EST)</option>
            <option value="America/Chicago">America/Chicago (CST)</option>
            <option value="America/Los_Angeles">America/Los_Angeles (PST)</option>
            <option value="Europe/London">Europe/London (GMT)</option>
            <option value="Europe/Istanbul">Europe/Istanbul (TRT)</option>
            <option value="Asia/Tokyo">Asia/Tokyo (JST)</option>
          </select>
        </div>
      </div>
      <SaveButton onClick={handleSave} />
    </SectionCard>
  );
}

function LLMProvidersTab() {
  const providers = [
    { id: "anthropic", name: "Anthropic", models: ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-haiku-35-20241022"], recommended: true },
    { id: "openai", name: "OpenAI", models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"], recommended: false },
    { id: "google", name: "Google", models: ["gemini-2.0-flash", "gemini-2.0-pro", "gemini-1.5-pro"], recommended: false },
    { id: "ollama", name: "Ollama", models: ["llama3:latest", "mistral:latest", "codellama:latest"], recommended: false },
  ];

  const [state, setState] = useState(
    Object.fromEntries(providers.map((p) => [p.id, { enabled: p.id === "anthropic", apiKey: "", model: p.models[0], isDefault: p.id === "anthropic" }]))
  );

  const update = (id: string, field: string, value: string | boolean) => {
    setState((prev) => {
      const current = prev[id]!;
      return { ...prev, [id]: { ...current, [field]: value } as typeof current };
    });
  };

  const handleTest = (name: string) => {
    toast.success(`${name} connection successful!`);
  };

  const handleSave = () => toast.success("LLM provider settings saved");

  return (
    <div className="space-y-4">
      {providers.map((p) => (
        <div key={p.id} className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center">
                <Key className="h-4 w-4 text-neutral-600 dark:text-neutral-400 dark:text-neutral-500" />
              </div>
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-semibold">{p.name}</h4>
                {p.recommended && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                    Recommended
                  </span>
                )}
                {state[p.id]?.isDefault && (
                  <span className="flex items-center gap-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300">
                    <Star className="h-2.5 w-2.5" /> Default
                  </span>
                )}
              </div>
            </div>
            <Toggle checked={state[p.id]?.enabled ?? false} onChange={(v) => update(p.id, "enabled", v)} label="" />
          </div>
          {state[p.id]?.enabled && (
            <div className="space-y-3 pl-11">
              <div>
                <label className="block text-xs font-medium mb-1">API Key</label>
                <PasswordInput value={state[p.id]?.apiKey ?? ""} onChange={(v) => update(p.id, "apiKey", v)} />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Default Model</label>
                <select className="input w-full" value={state[p.id]?.model ?? ""} onChange={(e) => update(p.id, "model", e.target.value)}>
                  {p.models.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <button onClick={() => handleTest(p.name)} className="text-xs font-medium px-3 py-1.5 rounded-md border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700 flex items-center gap-1.5">
                <TestTube2 className="h-3.5 w-3.5" /> Test Connection
              </button>
            </div>
          )}
        </div>
      ))}
      <SaveButton onClick={handleSave} />
    </div>
  );
}

function EmailTab() {
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpFrom, setSmtpFrom] = useState("");
  const [smtpTls, setSmtpTls] = useState(true);

  const handleSave = () => toast.success("Email settings saved");
  const handleTestEmail = () => toast.success("Test email sent!");

  return (
    <div className="space-y-6">
      <SectionCard title="Internal Mail Server" icon={Mail}>
        <div className="space-y-3 max-w-lg">
          <p className="text-sm text-neutral-600 dark:text-neutral-400 dark:text-neutral-500">Inter-agent email communication via aiosmtpd</p>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium mb-1">Host</label>
              <input className="input w-full bg-neutral-50 dark:bg-neutral-700" value="localhost" readOnly />
            </div>
            <div className="w-24">
              <label className="block text-xs font-medium mb-1">Port</label>
              <input className="input w-full bg-neutral-50 dark:bg-neutral-700" value="8025" readOnly />
            </div>
          </div>
        </div>
      </SectionCard>
      <SectionCard title="External SMTP" icon={Mail}>
        <div className="space-y-3 max-w-lg">
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium mb-1">SMTP Host</label>
              <input className="input w-full" value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} placeholder="smtp.gmail.com" />
            </div>
            <div className="w-24">
              <label className="block text-xs font-medium mb-1">Port</label>
              <input className="input w-full" value={smtpPort} onChange={(e) => setSmtpPort(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Username</label>
            <input className="input w-full" value={smtpUser} onChange={(e) => setSmtpUser(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Password</label>
            <PasswordInput value={smtpPassword} onChange={setSmtpPassword} placeholder="SMTP password" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">From Address</label>
            <input className="input w-full" value={smtpFrom} onChange={(e) => setSmtpFrom(e.target.value)} placeholder="noreply@company.com" />
          </div>
          <Toggle checked={smtpTls} onChange={setSmtpTls} label="Enable TLS" description="Use STARTTLS for secure connections" />
          <button onClick={handleTestEmail} className="text-xs font-medium px-3 py-1.5 rounded-md border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700 flex items-center gap-1.5">
            <TestTube2 className="h-3.5 w-3.5" /> Send Test Email
          </button>
        </div>
        <SaveButton onClick={handleSave} />
      </SectionCard>
    </div>
  );
}

function StorageTab() {
  const [retentionDays, setRetentionDays] = useState("90");
  const [autoCleanup, setAutoCleanup] = useState(true);
  const usedGB = 2.4;
  const totalGB = 50;
  const usedPercent = (usedGB / totalGB) * 100;

  const handleSave = () => toast.success("Storage settings saved");

  return (
    <SectionCard title="Object Storage (MinIO)" icon={HardDrive}>
      <div className="space-y-4 max-w-lg">
        <div>
          <label className="block text-xs font-medium mb-1">Endpoint</label>
          <input className="input w-full bg-neutral-50 dark:bg-neutral-700" value="minio:9000" readOnly />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Bucket</label>
          <input className="input w-full bg-neutral-50 dark:bg-neutral-700" value="whiteops-files" readOnly />
        </div>
        <div>
          <label className="block text-xs font-medium mb-2">Storage Usage</label>
          <div className="h-3 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-neutral-900 dark:bg-white rounded-full transition-all"
              style={{ width: `${usedPercent}%` }}
            />
          </div>
          <p className="text-xs text-neutral-500 mt-1">{usedGB} GB used of {totalGB} GB ({usedPercent.toFixed(1)}%)</p>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">File Retention (days)</label>
          <input className="input w-32" type="number" value={retentionDays} onChange={(e) => setRetentionDays(e.target.value)} />
        </div>
        <Toggle checked={autoCleanup} onChange={setAutoCleanup} label="Auto-Cleanup" description="Automatically delete files past retention period" />
      </div>
      <SaveButton onClick={handleSave} />
    </SectionCard>
  );
}

function SecurityTab() {
  return (
    <SectionCard title="Security Overview" icon={Shield}>
      <div className="space-y-4 max-w-lg">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg text-center">
            <p className="text-2xl font-bold">12+</p>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">Min Password Length</p>
          </div>
          <div className="p-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg text-center">
            <p className="text-2xl font-bold text-green-600 dark:text-green-400">Enabled</p>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">MFA Status</p>
          </div>
          <div className="p-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg text-center">
            <p className="text-2xl font-bold">3</p>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">Active Sessions</p>
          </div>
          <div className="p-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg text-center">
            <p className="text-2xl font-bold">5</p>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">IP Rules</p>
          </div>
        </div>
        <a
          href="/security"
          className="block card p-4 hover:shadow-md transition-shadow border-neutral-200 dark:border-neutral-700"
        >
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold">Go to Security Settings</h4>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">Configure password policies, IP rules, API keys, and more</p>
            </div>
            <Link2 className="h-5 w-5 text-neutral-400 dark:text-neutral-500" />
          </div>
        </a>
      </div>
    </SectionCard>
  );
}

function NotificationsTab() {
  const [slackWebhook, setSlackWebhook] = useState("https://hooks.slack.com/services/...");
  const [slackEnabled, setSlackEnabled] = useState(true);
  const [telegramToken, setTelegramToken] = useState("");
  const [telegramEnabled, setTelegramEnabled] = useState(false);
  const [emailEnabled, setEmailEnabled] = useState(true);

  const handleTest = (channel: string) => toast.success(`Test ${channel} notification sent!`);
  const handleSave = () => toast.success("Notification settings saved");

  return (
    <div className="space-y-6">
      <SectionCard title="Notification Channels" icon={Bell}>
        <div className="space-y-4 max-w-lg">
          {/* Slack */}
          <div className="p-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold">Slack</h4>
              <Toggle checked={slackEnabled} onChange={setSlackEnabled} label="" />
            </div>
            {slackEnabled && (
              <>
                <div>
                  <label className="block text-xs font-medium mb-1">Webhook URL</label>
                  <input className="input w-full" value={slackWebhook} onChange={(e) => setSlackWebhook(e.target.value)} placeholder="https://hooks.slack.com/services/..." />
                </div>
                <button onClick={() => handleTest("Slack")} className="text-xs font-medium px-3 py-1.5 rounded-md border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700 flex items-center gap-1.5">
                  <TestTube2 className="h-3.5 w-3.5" /> Test
                </button>
              </>
            )}
          </div>
          {/* Telegram */}
          <div className="p-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold">Telegram</h4>
              <Toggle checked={telegramEnabled} onChange={setTelegramEnabled} label="" />
            </div>
            {telegramEnabled && (
              <>
                <div>
                  <label className="block text-xs font-medium mb-1">Bot Token</label>
                  <PasswordInput value={telegramToken} onChange={setTelegramToken} placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v..." />
                </div>
                <button onClick={() => handleTest("Telegram")} className="text-xs font-medium px-3 py-1.5 rounded-md border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700 flex items-center gap-1.5">
                  <TestTube2 className="h-3.5 w-3.5" /> Test
                </button>
              </>
            )}
          </div>
          {/* Email */}
          <div className="p-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-semibold">Email</h4>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">Uses configured SMTP settings</p>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => handleTest("Email")} className="text-xs px-2 py-1 border border-neutral-200 dark:border-neutral-700 rounded hover:bg-neutral-100 dark:hover:bg-neutral-700">
                  Test
                </button>
                <Toggle checked={emailEnabled} onChange={setEmailEnabled} label="" />
              </div>
            </div>
          </div>
        </div>
      </SectionCard>
      <SectionCard title="Notification Routing" icon={Bell}>
        <div className="max-w-lg">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-neutral-500 border-b border-neutral-200 dark:border-neutral-700">
                <th className="pb-2">Severity</th>
                <th className="pb-2">Slack</th>
                <th className="pb-2">Email</th>
                <th className="pb-2">Telegram</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-700">
              {["Critical", "Warning", "Info"].map((sev) => (
                <tr key={sev}>
                  <td className="py-2 font-medium">{sev}</td>
                  <td className="py-2"><input type="checkbox" defaultChecked className="rounded" /></td>
                  <td className="py-2"><input type="checkbox" defaultChecked={sev !== "Info"} className="rounded" /></td>
                  <td className="py-2"><input type="checkbox" defaultChecked={sev === "Critical"} className="rounded" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <SaveButton onClick={handleSave} />
      </SectionCard>
    </div>
  );
}

function IntegrationsTab() {
  const integrations = [
    { id: "github", name: "GitHub", description: "Repository management, PRs, issues" },
    { id: "jira", name: "Jira", description: "Issue tracking and project management" },
    { id: "slack", name: "Slack", description: "Team messaging and notifications" },
    { id: "discord", name: "Discord", description: "Community and team communication" },
    { id: "notion", name: "Notion", description: "Knowledge base and documentation" },
    { id: "pagerduty", name: "PagerDuty", description: "Incident management and alerting" },
    { id: "sentry", name: "Sentry", description: "Error tracking and performance monitoring" },
    { id: "linear", name: "Linear", description: "Issue tracking and project planning" },
  ];

  const [state, setState] = useState(
    Object.fromEntries(integrations.map((i) => [
      i.id,
      { connected: i.id === "github" || i.id === "slack", token: "" },
    ]))
  );

  const handleConnect = (id: string) => {
    setState((prev) => {
      const current = prev[id]!;
      return { ...prev, [id]: { ...current, connected: true } as typeof current };
    });
    toast.success(`${id} connected!`);
  };

  const handleDisconnect = (id: string) => {
    setState((prev) => {
      const current = prev[id]!;
      return { ...prev, [id]: { ...current, connected: false, token: "" } as typeof current };
    });
    toast.success(`${id} disconnected`);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {integrations.map((integ) => (
        <div key={integ.id} className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center">
                <Plug className="h-4 w-4 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />
              </div>
              <div>
                <h4 className="text-sm font-semibold">{integ.name}</h4>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{integ.description}</p>
              </div>
            </div>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
              state[integ.id]?.connected
                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                : "bg-neutral-100 text-neutral-500 dark:bg-neutral-700 dark:text-neutral-400 dark:text-neutral-500"
            }`}>
              {state[integ.id]?.connected ? "Connected" : "Disconnected"}
            </span>
          </div>
          {!state[integ.id]?.connected ? (
            <div className="space-y-2">
              <PasswordInput
                value={state[integ.id]?.token ?? ""}
                onChange={(v) => setState((prev) => { const c = prev[integ.id]!; return { ...prev, [integ.id]: { ...c, token: v } as typeof c }; })}
                placeholder={`${integ.name} API token...`}
              />
              <button onClick={() => handleConnect(integ.id)} className="text-xs font-medium px-3 py-1.5 rounded-md bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 hover:opacity-80 transition-opacity">
                Connect
              </button>
            </div>
          ) : (
            <div className="flex gap-2">
              <button onClick={() => handleDisconnect(integ.id)} className="text-xs px-3 py-1.5 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400 rounded-md hover:bg-red-50 dark:hover:bg-red-950">
                Disconnect
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function BackupsTab() {
  const [schedule, setSchedule] = useState("daily");
  const [retentionDays, setRetentionDays] = useState("30");
  const backupHistory = [
    { id: "1", date: "2025-04-08 02:00 AM", size: "1.2 GB", status: "success" },
    { id: "2", date: "2025-04-07 02:00 AM", size: "1.1 GB", status: "success" },
    { id: "3", date: "2025-04-06 02:00 AM", size: "1.1 GB", status: "failed" },
  ];

  const handleBackupNow = () => toast.success("Backup started...");
  const handleSave = () => toast.success("Backup settings saved");

  return (
    <div className="space-y-6">
      <SectionCard title="Backup Configuration" icon={Database}>
        <div className="space-y-4 max-w-lg">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg">
              <p className="text-xs text-neutral-500 mb-1">Last Backup</p>
              <p className="text-sm font-semibold">2025-04-08 02:00 AM</p>
            </div>
            <div className="p-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg">
              <p className="text-xs text-neutral-500 mb-1">Storage Used</p>
              <p className="text-sm font-semibold">3.4 GB</p>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Schedule</label>
            <select className="input w-48" value={schedule} onChange={(e) => setSchedule(e.target.value)}>
              <option value="daily">Daily (2:00 AM)</option>
              <option value="weekly">Weekly (Sunday 2:00 AM)</option>
              <option value="monthly">Monthly (1st, 2:00 AM)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Retention (days)</label>
            <input className="input w-32" type="number" value={retentionDays} onChange={(e) => setRetentionDays(e.target.value)} />
          </div>
          <button onClick={handleBackupNow} className="btn-primary flex items-center gap-1.5 text-xs">
            <Download className="h-3.5 w-3.5" /> Backup Now
          </button>
        </div>
      </SectionCard>
      <SectionCard title="Backup History" icon={Clock}>
        <div className="max-w-lg">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-neutral-500 border-b border-neutral-200 dark:border-neutral-700">
                <th className="pb-2">Date</th>
                <th className="pb-2">Size</th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-700">
              {backupHistory.map((b) => (
                <tr key={b.id}>
                  <td className="py-2">{b.date}</td>
                  <td className="py-2">{b.size}</td>
                  <td className="py-2">
                    {b.status === "success" ? (
                      <span className="flex items-center gap-1 text-green-600"><CheckCircle className="h-3.5 w-3.5" /> Success</span>
                    ) : (
                      <span className="flex items-center gap-1 text-red-500"><XCircle className="h-3.5 w-3.5" /> Failed</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <SaveButton onClick={handleSave} />
      </SectionCard>
    </div>
  );
}

function FeatureFlagsTab() {
  const [flags, setFlags] = useState({
    mfa: true,
    webhooks: true,
    costTracking: true,
    circuitBreakers: true,
    agentMemory: true,
    triggers: true,
    marketplace: true,
    chatInterface: false,
  });

  const toggleFlag = (key: string) => {
    setFlags((prev) => ({ ...prev, [key]: !prev[key as keyof typeof prev] }));
  };

  const handleSave = () => toast.success("Feature flags saved");

  const flagList = [
    { key: "mfa", label: "Multi-Factor Authentication", description: "Require MFA for user accounts" },
    { key: "webhooks", label: "Webhooks", description: "Allow webhook integrations for event notifications" },
    { key: "costTracking", label: "Cost Tracking", description: "Track LLM API costs per agent and task" },
    { key: "circuitBreakers", label: "Circuit Breakers", description: "Enable circuit breakers for external services" },
    { key: "agentMemory", label: "Agent Memory", description: "Long-term memory for agents across tasks" },
    { key: "triggers", label: "Triggers & Automation", description: "Event-driven triggers and scheduled automation" },
    { key: "marketplace", label: "Marketplace", description: "Agent template marketplace" },
    { key: "chatInterface", label: "Chat Interface", description: "Direct chat with agents (experimental)" },
  ];

  return (
    <SectionCard title="Feature Flags" icon={ToggleLeft}>
      <div className="space-y-1 max-w-lg">
        {flagList.map((f) => (
          <Toggle
            key={f.key}
            checked={flags[f.key as keyof typeof flags]}
            onChange={() => toggleFlag(f.key)}
            label={f.label}
            description={f.description}
          />
        ))}
      </div>
      <SaveButton onClick={handleSave} />
    </SectionCard>
  );
}

function DangerZoneTab() {
  const [confirmReset, setConfirmReset] = useState(false);
  const [confirmFactory, setConfirmFactory] = useState(0); // 0 = idle, 1 = first confirm, 2 = second confirm
  const [purgeFrom, setPurgeFrom] = useState("");
  const [purgeTo, setPurgeTo] = useState("");

  const handleResetDemo = () => {
    if (!confirmReset) {
      setConfirmReset(true);
      return;
    }
    toast.success("Demo data has been reset");
    setConfirmReset(false);
  };

  const handlePurgeAudit = () => {
    if (!purgeFrom || !purgeTo) {
      toast.error("Please select a date range");
      return;
    }
    toast.success("Audit logs purged for selected range");
  };

  const handleFactoryReset = () => {
    if (confirmFactory < 2) {
      setConfirmFactory((prev) => prev + 1);
      return;
    }
    toast.success("Factory reset initiated...");
    setConfirmFactory(0);
  };

  return (
    <div className="space-y-4 max-w-lg">
      <div className="border-2 border-red-200 dark:border-red-900 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-red-600 dark:text-red-400 mb-4 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" /> Danger Zone
        </h3>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-6">
          These actions are destructive and cannot be undone. Proceed with caution.
        </p>
        <div className="space-y-6">
          {/* Reset Demo Data */}
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold">Reset Demo Data</h4>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">Restore all data to initial demo state</p>
            </div>
            {confirmReset ? (
              <div className="flex gap-2">
                <button onClick={() => setConfirmReset(false)} className="text-xs px-3 py-1.5 border border-neutral-200 dark:border-neutral-700 rounded-md hover:bg-neutral-50 dark:hover:bg-neutral-700">
                  Cancel
                </button>
                <button onClick={handleResetDemo} className="text-xs font-medium px-3 py-1.5 rounded-md bg-red-600 text-white hover:bg-red-700">
                  Confirm Reset
                </button>
              </div>
            ) : (
              <button onClick={handleResetDemo} className="text-xs font-medium px-3 py-1.5 rounded-md border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950">
                Reset
              </button>
            )}
          </div>

          <hr className="border-red-100 dark:border-red-900" />

          {/* Purge Audit Logs */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div>
                <h4 className="text-sm font-semibold">Purge Audit Logs</h4>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">Delete audit log entries within a date range</p>
              </div>
            </div>
            <div className="flex gap-2 items-end">
              <div>
                <label className="block text-xs text-neutral-500 mb-1">From</label>
                <input type="date" className="input text-xs" value={purgeFrom} onChange={(e) => setPurgeFrom(e.target.value)} />
              </div>
              <div>
                <label className="block text-xs text-neutral-500 mb-1">To</label>
                <input type="date" className="input text-xs" value={purgeTo} onChange={(e) => setPurgeTo(e.target.value)} />
              </div>
              <button onClick={handlePurgeAudit} className="text-xs font-medium px-3 py-1.5 rounded-md border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950">
                Purge
              </button>
            </div>
          </div>

          <hr className="border-red-100 dark:border-red-900" />

          {/* Factory Reset */}
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold">Factory Reset</h4>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">Erase all data and restore default settings</p>
            </div>
            {confirmFactory === 0 ? (
              <button onClick={handleFactoryReset} className="text-xs font-medium px-3 py-1.5 rounded-md border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 flex items-center gap-1.5">
                <Trash2 className="h-3.5 w-3.5" /> Factory Reset
              </button>
            ) : confirmFactory === 1 ? (
              <div className="flex gap-2">
                <button onClick={() => setConfirmFactory(0)} className="text-xs px-3 py-1.5 border border-neutral-200 dark:border-neutral-700 rounded-md hover:bg-neutral-50 dark:hover:bg-neutral-700">
                  Cancel
                </button>
                <button onClick={handleFactoryReset} className="text-xs font-medium px-3 py-1.5 rounded-md bg-red-600 text-white hover:bg-red-700">
                  Are you sure?
                </button>
              </div>
            ) : (
              <div className="flex gap-2">
                <button onClick={() => setConfirmFactory(0)} className="text-xs px-3 py-1.5 border border-neutral-200 dark:border-neutral-700 rounded-md hover:bg-neutral-50 dark:hover:bg-neutral-700">
                  Cancel
                </button>
                <button onClick={handleFactoryReset} className="text-xs font-bold px-3 py-1.5 rounded-md bg-red-700 text-white hover:bg-red-800 animate-pulse">
                  CONFIRM FACTORY RESET
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- Main Settings Page ----

export default function Settings() {
  const [activeTab, setActiveTab] = useState("general");

  const { data: healthData } = useQuery({
    queryKey: ["system-health"],
    queryFn: () => settingsApi.health(),
    refetchInterval: 30000,
  });

  const health = healthData?.data;

  const renderTab = () => {
    switch (activeTab) {
      case "general": return <GeneralTab />;
      case "llm": return <LLMProvidersTab />;
      case "email": return <EmailTab />;
      case "storage": return <StorageTab />;
      case "security": return <SecurityTab />;
      case "notifications": return <NotificationsTab />;
      case "integrations": return <IntegrationsTab />;
      case "backups": return <BackupsTab />;
      case "features": return <FeatureFlagsTab />;
      case "danger": return <DangerZoneTab />;
      default: return <GeneralTab />;
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <SettingsIcon className="h-6 w-6 text-neutral-700 dark:text-neutral-300" />
          <div>
            <h1 className="text-2xl font-bold">Settings</h1>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">Configure your White-Ops platform</p>
          </div>
        </div>
        {health && (
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${
              health.overall === "healthy"
                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
            }`}>
              {health.overall === "healthy" ? <CheckCircle className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
              System {health.overall}
            </span>
          </div>
        )}
      </div>

      {/* Inline Tab Navigation */}
      <div className="mb-6 overflow-x-auto">
        <div className="flex gap-1 border-b border-neutral-200 dark:border-neutral-700">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-3 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                activeTab === id
                  ? "border-neutral-900 dark:border-white text-neutral-900 dark:text-white"
                  : "border-transparent text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300 hover:border-neutral-300 dark:hover:border-neutral-600"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-4xl">{renderTab()}</div>
    </div>
  );
}
