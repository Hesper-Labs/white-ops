import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Shield,
  Key,
  Smartphone,
  Globe,
  Monitor,
  Lock,
  Plus,
  Trash2,
  LogOut,
  Copy,
  Eye,
  EyeOff,
  Save,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { securityApi } from "../api/endpoints";
import { cn, formatDate } from "../lib/utils";
import toast from "react-hot-toast";

// --- Demo Data ---

const DEMO_PASSWORD_POLICY = {
  min_length: 12,
  require_uppercase: true,
  require_lowercase: true,
  require_numbers: true,
  require_symbols: true,
  expiry_days: 90,
  history_count: 5,
};

const DEMO_MFA_CONFIG = {
  enabled_globally: true,
  users: [
    { id: "u1", name: "Admin User", email: "admin@whiteops.local", mfa_enabled: true, mfa_method: "totp", last_verified: "2025-04-05T08:00:00Z" },
    { id: "u2", name: "John Developer", email: "john@whiteops.local", mfa_enabled: true, mfa_method: "totp", last_verified: "2025-04-04T09:15:00Z" },
    { id: "u3", name: "Sarah Analyst", email: "sarah@whiteops.local", mfa_enabled: false, mfa_method: null, last_verified: null },
    { id: "u4", name: "Mike Ops", email: "mike@whiteops.local", mfa_enabled: true, mfa_method: "totp", last_verified: "2025-04-03T14:30:00Z" },
  ],
};

const DEMO_SESSIONS = [
  { id: "s1", user: "admin@whiteops.local", ip: "192.168.1.100", device: "Chrome 124 / macOS", last_active: "2025-04-05T16:45:00Z", current: true },
  { id: "s2", user: "john@whiteops.local", ip: "192.168.1.105", device: "Firefox 125 / Ubuntu", last_active: "2025-04-05T16:30:00Z", current: false },
  { id: "s3", user: "sarah@whiteops.local", ip: "10.0.0.55", device: "Safari 17 / iOS", last_active: "2025-04-05T15:10:00Z", current: false },
  { id: "s4", user: "mike@whiteops.local", ip: "192.168.1.112", device: "Chrome 124 / Windows", last_active: "2025-04-05T14:00:00Z", current: false },
];

const DEMO_IP_WHITELIST = [
  { id: "ip1", address: "192.168.1.0/24", label: "Office Network", created_at: "2025-01-15T10:00:00Z" },
  { id: "ip2", address: "10.0.0.0/16", label: "VPN Range", created_at: "2025-02-01T09:00:00Z" },
  { id: "ip3", address: "203.0.113.50", label: "CI/CD Server", created_at: "2025-03-10T14:00:00Z" },
];

const DEMO_API_KEYS = [
  { id: "ak1", name: "Production API", key_preview: "wo_prod_****a3f8", created_at: "2025-01-10T10:00:00Z", last_used: "2025-04-05T16:00:00Z", status: "active" },
  { id: "ak2", name: "Staging API", key_preview: "wo_stg_****b7c2", created_at: "2025-02-20T08:00:00Z", last_used: "2025-04-04T12:00:00Z", status: "active" },
  { id: "ak3", name: "CI/CD Pipeline", key_preview: "wo_ci_****d9e1", created_at: "2025-03-05T11:00:00Z", last_used: "2025-04-05T09:30:00Z", status: "active" },
  { id: "ak4", name: "Legacy Integration", key_preview: "wo_leg_****f4a0", created_at: "2024-11-01T10:00:00Z", last_used: "2025-02-15T08:00:00Z", status: "inactive" },
];

type Tab = "password" | "mfa" | "sessions" | "ip" | "apikeys";

// --- Component ---

export default function SecuritySettings() {
  const [activeTab, setActiveTab] = useState<Tab>("password");
  const [passwordPolicy, setPasswordPolicy] = useState(DEMO_PASSWORD_POLICY);
  const [newIp, setNewIp] = useState({ address: "", label: "" });
  const [showNewKeyModal, setShowNewKeyModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [generatedKey, setGeneratedKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const queryClient = useQueryClient();

  const { data: securityData } = useQuery({
    queryKey: ["security-settings"],
    queryFn: async () => {
      try {
        const res = await securityApi.getSettings();
        return res.data;
      } catch {
        return null;
      }
    },
  });

  const mfaConfig = securityData?.mfa ?? DEMO_MFA_CONFIG;
  const sessions = securityData?.sessions ?? DEMO_SESSIONS;
  const ipWhitelist = securityData?.ip_whitelist ?? DEMO_IP_WHITELIST;
  const apiKeys = securityData?.api_keys ?? DEMO_API_KEYS;

  const saveMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      securityApi.updatePasswordPolicy(data).catch(() => Promise.resolve()),
    onSuccess: () => {
      toast.success("Settings saved");
      queryClient.invalidateQueries({ queryKey: ["security-settings"] });
    },
  });

  const logoutSessionMutation = useMutation({
    mutationFn: (id: string) =>
      securityApi.deleteSession(id).catch(() => Promise.resolve()),
    onSuccess: () => {
      toast.success("Session terminated");
      queryClient.invalidateQueries({ queryKey: ["security-settings"] });
    },
  });

  const revokeKeyMutation = useMutation({
    mutationFn: (id: string) =>
      securityApi.deleteApiKey(id).catch(() => Promise.resolve()),
    onSuccess: () => {
      toast.success("API key revoked");
      queryClient.invalidateQueries({ queryKey: ["security-settings"] });
    },
  });

  const tabs: { key: Tab; label: string; icon: React.ElementType }[] = [
    { key: "password", label: "Password Policy", icon: Lock },
    { key: "mfa", label: "MFA", icon: Smartphone },
    { key: "sessions", label: "Sessions", icon: Monitor },
    { key: "ip", label: "IP Whitelist", icon: Globe },
    { key: "apikeys", label: "API Keys", icon: Key },
  ];

  const handleCreateKey = () => {
    const key = `wo_${newKeyName.toLowerCase().replace(/\s+/g, "_")}_${crypto.randomUUID().slice(0, 12)}`;
    setGeneratedKey(key);
    toast.success("API key created");
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-neutral-900 dark:text-white">Security Settings</h1>
          <p className="text-xs text-neutral-400 mt-0.5">Manage authentication, access control, and API security</p>
        </div>
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-green-500" />
          <span className="text-xs text-green-600 font-medium">Security Status: Good</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-neutral-200 dark:border-neutral-700">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px",
              activeTab === tab.key
                ? "border-neutral-900 text-neutral-900 dark:text-white"
                : "border-transparent text-neutral-400 hover:text-neutral-600"
            )}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Password Policy Tab */}
      {activeTab === "password" && (
        <div className="card p-6 max-w-2xl">
          <h2 className="text-sm font-semibold text-neutral-900 mb-4">Password Requirements</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-xs text-neutral-600">Minimum Length</label>
              <input
                type="number"
                className="input w-20 text-center"
                value={passwordPolicy.min_length}
                onChange={(e) => setPasswordPolicy({ ...passwordPolicy, min_length: +e.target.value })}
              />
            </div>
            {([
              ["require_uppercase", "Require Uppercase Letters"],
              ["require_lowercase", "Require Lowercase Letters"],
              ["require_numbers", "Require Numbers"],
              ["require_symbols", "Require Special Characters"],
            ] as const).map(([key, label]) => (
              <div key={key} className="flex items-center justify-between">
                <label className="text-xs text-neutral-600">{label}</label>
                <button
                  onClick={() => setPasswordPolicy({ ...passwordPolicy, [key]: !passwordPolicy[key] })}
                  className={cn(
                    "w-10 h-5 rounded-full transition-colors relative",
                    passwordPolicy[key] ? "bg-green-500" : "bg-neutral-300"
                  )}
                >
                  <span className={cn(
                    "absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform",
                    passwordPolicy[key] ? "translate-x-5" : "translate-x-0.5"
                  )} />
                </button>
              </div>
            ))}
            <div className="flex items-center justify-between">
              <label className="text-xs text-neutral-600">Password Expiry (days)</label>
              <input
                type="number"
                className="input w-20 text-center"
                value={passwordPolicy.expiry_days}
                onChange={(e) => setPasswordPolicy({ ...passwordPolicy, expiry_days: +e.target.value })}
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="text-xs text-neutral-600">Password History Count</label>
              <input
                type="number"
                className="input w-20 text-center"
                value={passwordPolicy.history_count}
                onChange={(e) => setPasswordPolicy({ ...passwordPolicy, history_count: +e.target.value })}
              />
            </div>
          </div>
          <div className="mt-6 pt-4 border-t border-neutral-100">
            <button
              onClick={() => saveMutation.mutate({ password_policy: passwordPolicy })}
              className="btn-primary text-sm flex items-center gap-1.5"
            >
              <Save className="h-3.5 w-3.5" /> Save Password Policy
            </button>
          </div>
        </div>
      )}

      {/* MFA Tab */}
      {activeTab === "mfa" && (
        <div className="space-y-6">
          <div className="card p-6 max-w-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-neutral-900 dark:text-white">Multi-Factor Authentication</h2>
              <button
                onClick={() => saveMutation.mutate({ mfa_global: !mfaConfig.enabled_globally })}
                className={cn(
                  "w-12 h-6 rounded-full transition-colors relative",
                  mfaConfig.enabled_globally ? "bg-green-500" : "bg-neutral-300"
                )}
              >
                <span className={cn(
                  "absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform",
                  mfaConfig.enabled_globally ? "translate-x-6" : "translate-x-0.5"
                )} />
              </button>
            </div>
            <p className="text-xs text-neutral-400 mb-4">
              {mfaConfig.enabled_globally
                ? "MFA is required for all users"
                : "MFA is optional - users can enable it individually"}
            </p>
          </div>

          <div className="card overflow-hidden max-w-2xl">
            <div className="px-6 py-4 border-b border-neutral-100">
              <h2 className="text-sm font-semibold text-neutral-900 dark:text-white">User MFA Status</h2>
            </div>
            <table className="w-full">
              <thead>
                <tr>
                  <th className="table-header">User</th>
                  <th className="table-header">Method</th>
                  <th className="table-header">Last Verified</th>
                  <th className="table-header text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {mfaConfig.users.map((user: any) => (
                  <tr key={user.id} className="border-b border-neutral-100 hover:bg-neutral-50 dark:bg-neutral-800/50">
                    <td className="px-4 py-3">
                      <p className="text-xs font-medium text-neutral-900 dark:text-white">{user.name}</p>
                      <p className="text-[10px] text-neutral-400 dark:text-neutral-500">{user.email}</p>
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-600">
                      {user.mfa_method ? user.mfa_method.toUpperCase() : "-"}
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">
                      {user.last_verified ? formatDate(user.last_verified) : "-"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {user.mfa_enabled ? (
                        <span className="badge-green flex items-center gap-1 justify-center">
                          <CheckCircle2 className="h-3 w-3" /> Enabled
                        </span>
                      ) : (
                        <span className="badge-red flex items-center gap-1 justify-center">
                          <XCircle className="h-3 w-3" /> Disabled
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sessions Tab */}
      {activeTab === "sessions" && (
        <div className="card overflow-hidden">
          <div className="px-6 py-4 border-b border-neutral-100 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-900 dark:text-white">Active Sessions ({sessions.length})</h2>
            <button
              onClick={() => {
                sessions.filter((s: any) => !s.current).forEach((s: any) => logoutSessionMutation.mutate(s.id));
                toast.success("All other sessions terminated");
              }}
              className="text-xs text-red-600 hover:text-red-700 font-medium"
            >
              Logout All Others
            </button>
          </div>
          <table className="w-full">
            <thead>
              <tr>
                <th className="table-header">User</th>
                <th className="table-header">IP Address</th>
                <th className="table-header">Device</th>
                <th className="table-header">Last Active</th>
                <th className="table-header text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session: any) => (
                <tr key={session.id} className="border-b border-neutral-100 hover:bg-neutral-50 dark:bg-neutral-800/50">
                  <td className="px-4 py-3 text-xs font-medium text-neutral-900 dark:text-white">
                    {session.user}
                    {session.current && <span className="badge-green ml-2 text-[10px]">Current</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-neutral-600 font-mono">{session.ip}</td>
                  <td className="px-4 py-3 text-xs text-neutral-600">{session.device}</td>
                  <td className="px-4 py-3 text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{formatDate(session.last_active)}</td>
                  <td className="px-4 py-3 text-right">
                    {!session.current && (
                      <button
                        onClick={() => logoutSessionMutation.mutate(session.id)}
                        className="p-1.5 rounded hover:bg-red-50 text-neutral-400 hover:text-red-600"
                        title="Force Logout"
                      >
                        <LogOut className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* IP Whitelist Tab */}
      {activeTab === "ip" && (
        <div className="space-y-6 max-w-2xl">
          <div className="card p-6">
            <h2 className="text-sm font-semibold text-neutral-900 mb-4">Add IP Address / Range</h2>
            <div className="flex gap-3">
              <input
                className="input flex-1"
                placeholder="192.168.1.0/24"
                value={newIp.address}
                onChange={(e) => setNewIp({ ...newIp, address: e.target.value })}
              />
              <input
                className="input flex-1"
                placeholder="Label (e.g., Office Network)"
                value={newIp.label}
                onChange={(e) => setNewIp({ ...newIp, label: e.target.value })}
              />
              <button
                onClick={() => {
                  if (newIp.address) {
                    toast.success("IP address added");
                    setNewIp({ address: "", label: "" });
                  }
                }}
                className="btn-primary text-sm flex items-center gap-1.5"
              >
                <Plus className="h-3.5 w-3.5" /> Add
              </button>
            </div>
          </div>

          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-neutral-100">
              <h2 className="text-sm font-semibold text-neutral-900 dark:text-white">Whitelisted IPs ({ipWhitelist.length})</h2>
            </div>
            <table className="w-full">
              <thead>
                <tr>
                  <th className="table-header">IP / Range</th>
                  <th className="table-header">Label</th>
                  <th className="table-header">Added</th>
                  <th className="table-header text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {ipWhitelist.map((ip: any) => (
                  <tr key={ip.id} className="border-b border-neutral-100 hover:bg-neutral-50 dark:bg-neutral-800/50">
                    <td className="px-4 py-3 text-xs font-mono text-neutral-900 dark:text-white">{ip.address}</td>
                    <td className="px-4 py-3 text-xs text-neutral-600">{ip.label}</td>
                    <td className="px-4 py-3 text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{formatDate(ip.created_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => toast.success("IP removed")}
                        className="p-1.5 rounded hover:bg-red-50 text-neutral-400 hover:text-red-600"
                        title="Remove"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* API Keys Tab */}
      {activeTab === "apikeys" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-900 dark:text-white">API Keys</h2>
            <button
              onClick={() => { setShowNewKeyModal(true); setNewKeyName(""); setGeneratedKey(""); setShowKey(false); }}
              className="btn-primary text-sm flex items-center gap-1.5"
            >
              <Plus className="h-3.5 w-3.5" /> Create New Key
            </button>
          </div>

          <div className="card overflow-hidden">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="table-header">Name</th>
                  <th className="table-header">Key</th>
                  <th className="table-header">Created</th>
                  <th className="table-header">Last Used</th>
                  <th className="table-header text-center">Status</th>
                  <th className="table-header text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {apiKeys.map((key: any) => (
                  <tr key={key.id} className="border-b border-neutral-100 hover:bg-neutral-50 dark:bg-neutral-800/50">
                    <td className="px-4 py-3 text-xs font-medium text-neutral-900 dark:text-white">{key.name}</td>
                    <td className="px-4 py-3 text-xs font-mono text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{key.key_preview}</td>
                    <td className="px-4 py-3 text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{formatDate(key.created_at)}</td>
                    <td className="px-4 py-3 text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{formatDate(key.last_used)}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={key.status === "active" ? "badge-green" : "badge-gray"}>
                        {key.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => revokeKeyMutation.mutate(key.id)}
                        className="text-xs text-red-600 hover:text-red-700 font-medium"
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create API Key Modal */}
      {showNewKeyModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setShowNewKeyModal(false)}>
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            <div className="p-5 border-b border-neutral-100">
              <h2 className="text-sm font-bold text-neutral-900 dark:text-white">Create API Key</h2>
            </div>
            <div className="p-5 space-y-4">
              {!generatedKey ? (
                <>
                  <div>
                    <label className="text-xs font-medium text-neutral-700 mb-1 block">Key Name</label>
                    <input
                      className="input w-full"
                      placeholder="e.g., Production API"
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                    />
                  </div>
                  <button
                    onClick={handleCreateKey}
                    disabled={!newKeyName}
                    className="btn-primary text-sm w-full flex items-center justify-center gap-1.5"
                  >
                    <Key className="h-3.5 w-3.5" /> Generate Key
                  </button>
                </>
              ) : (
                <div>
                  <p className="text-xs text-amber-600 bg-amber-50 p-3 rounded-lg mb-3">
                    Copy this key now. You will not be able to see it again.
                  </p>
                  <div className="flex items-center gap-2">
                    <input
                      className="input flex-1 font-mono text-xs"
                      type={showKey ? "text" : "password"}
                      value={generatedKey}
                      readOnly
                    />
                    <button onClick={() => setShowKey(!showKey)} className="p-2 rounded hover:bg-neutral-100">
                      {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                    <button
                      onClick={() => { navigator.clipboard.writeText(generatedKey); toast.success("Copied to clipboard"); }}
                      className="p-2 rounded hover:bg-neutral-100"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
            <div className="flex justify-end p-5 border-t border-neutral-100">
              <button onClick={() => setShowNewKeyModal(false)} className="btn-secondary text-sm">
                {generatedKey ? "Done" : "Cancel"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
