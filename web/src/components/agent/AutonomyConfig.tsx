import { useState } from "react";
import { Save, Shield, ShieldAlert, ShieldCheck, ShieldOff, Ban, DollarSign, Cpu } from "lucide-react";
import toast from "react-hot-toast";

const AUTONOMY_LEVELS = [
  {
    value: "autonomous",
    label: "Autonomous",
    icon: ShieldCheck,
    color: "text-neutral-500",
    dotColor: "bg-emerald-500",
    bgColor: "bg-neutral-50 dark:bg-neutral-800/50",
    borderColor: "border-neutral-300 dark:border-neutral-600",
    description: "Agent executes all tools without approval",
  },
  {
    value: "cautious",
    label: "Cautious",
    icon: Shield,
    color: "text-neutral-500",
    dotColor: "bg-amber-500",
    bgColor: "bg-neutral-50 dark:bg-neutral-800/50",
    borderColor: "border-neutral-300 dark:border-neutral-600",
    description: "Agent asks before dangerous operations (shell, docker, terraform, file delete)",
  },
  {
    value: "supervised",
    label: "Supervised",
    icon: ShieldAlert,
    color: "text-neutral-500",
    dotColor: "bg-amber-500",
    bgColor: "bg-neutral-50 dark:bg-neutral-800/50",
    borderColor: "border-neutral-300 dark:border-neutral-600",
    description: "Agent asks before every tool call",
  },
  {
    value: "read_only",
    label: "Read Only",
    icon: ShieldOff,
    color: "text-neutral-500",
    dotColor: "bg-red-500",
    bgColor: "bg-neutral-50 dark:bg-neutral-800/50",
    borderColor: "border-neutral-300 dark:border-neutral-600",
    description: "Agent can only search, browse, and analyze -- no writes",
  },
] as const;

const ALL_TOOLS = [
  "shell", "docker_ops", "terraform", "code_exec", "file_manager",
  "database", "ssh_manager", "git_ops", "api_caller", "webhook",
  "browser", "web_scraper", "search", "rss_feed", "data_analysis",
  "data_visualization", "excel", "word", "powerpoint", "pdf",
  "internal_email", "external_email", "slack", "teams", "sms",
  "calendar", "translator", "ocr", "crm", "erp",
  "project_management", "invoice_generator", "accounting",
  "expense_tracker", "leave_management", "employee_directory",
  "health_checker", "prometheus", "log_analyzer", "text_summarizer",
];

interface AutonomyConfigProps {
  agent: any;
  onSave: (config: any) => void;
}

export default function AutonomyConfig({ agent, onSave }: AutonomyConfigProps) {
  const [level, setLevel] = useState<string>(agent.autonomy_level ?? "autonomous");
  const [blacklist, setBlacklist] = useState<string[]>(agent.tool_blacklist ?? []);
  const [riskRules, setRiskRules] = useState({
    max_file_delete_mb: agent.risk_rules?.max_file_delete_mb ?? 100,
    block_external_api: agent.risk_rules?.block_external_api ?? false,
    require_approval_for: agent.risk_rules?.require_approval_for ?? [],
  });
  const [dailyBudget, setDailyBudget] = useState<number>(agent.daily_budget_usd ?? 0);
  const [maxTokens, setMaxTokens] = useState<number>(agent.max_tokens_per_task ?? 0);

  const handleSave = () => {
    onSave({
      autonomy_level: level,
      tool_blacklist: blacklist,
      risk_rules: riskRules,
      daily_budget_usd: dailyBudget,
      max_tokens_per_task: maxTokens,
    });
    toast.success("Autonomy settings saved");
  };

  const toggleBlacklist = (tool: string) => {
    setBlacklist((prev) =>
      prev.includes(tool) ? prev.filter((t) => t !== tool) : [...prev, tool]
    );
  };

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Autonomy Level */}
      <div className="card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Autonomy Level</h3>
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          Controls how much freedom the agent has when executing tools.
        </p>
        <div className="grid grid-cols-2 gap-3">
          {AUTONOMY_LEVELS.map((opt) => {
            const Icon = opt.icon;
            const selected = level === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setLevel(opt.value)}
                className={`flex items-start gap-3 p-3.5 rounded-lg border-2 text-left transition-all ${
                  selected
                    ? `${opt.borderColor} ${opt.bgColor}`
                    : "border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600"
                }`}
              >
                <Icon className={`h-5 w-5 mt-0.5 shrink-0 ${selected ? opt.color : "text-neutral-400"}`} />
                <div>
                  <p className={`text-sm font-semibold flex items-center gap-2 ${selected ? "text-neutral-900 dark:text-neutral-100" : "text-neutral-600 dark:text-neutral-400"}`}>
                    <span className={`w-2 h-2 rounded-full ${opt.dotColor}`} />
                    {opt.label}
                  </p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">{opt.description}</p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Tool Blacklist */}
      <div className="card p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Ban className="h-4 w-4 text-red-500" />
          <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Tool Blacklist</h3>
          <span className="text-xs text-neutral-400 dark:text-neutral-500">({blacklist.length} blocked)</span>
        </div>
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          Select tools that this agent should never be allowed to use, regardless of autonomy level.
        </p>
        <div className="grid grid-cols-4 gap-2 max-h-48 overflow-y-auto">
          {ALL_TOOLS.map((tool) => (
            <label key={tool} className="flex items-center gap-2 cursor-pointer group">
              <input
                type="checkbox"
                checked={blacklist.includes(tool)}
                onChange={() => toggleBlacklist(tool)}
                className="w-3.5 h-3.5 rounded border-neutral-300 dark:border-neutral-600 text-red-600 focus:ring-red-500 cursor-pointer"
              />
              <span className={`text-xs font-mono ${
                blacklist.includes(tool)
                  ? "text-red-600 dark:text-red-400 line-through"
                  : "text-neutral-600 dark:text-neutral-400 group-hover:text-neutral-900 dark:group-hover:text-neutral-200"
              }`}>
                {tool}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Risk Rules */}
      <div className="card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Risk Rules</h3>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
              Max File Delete Size (MB)
            </label>
            <input
              type="number"
              className="input"
              min={0}
              value={riskRules.max_file_delete_mb}
              onChange={(e) => setRiskRules((r) => ({ ...r, max_file_delete_mb: parseInt(e.target.value) || 0 }))}
              placeholder="0 = unlimited"
            />
            <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-1">0 = no limit</p>
          </div>

          <div className="flex items-start gap-3 pt-5">
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={riskRules.block_external_api}
                onChange={(e) => setRiskRules((r) => ({ ...r, block_external_api: e.target.checked }))}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-neutral-200 dark:bg-neutral-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-red-500" />
            </label>
            <div>
              <p className="text-xs font-medium text-neutral-700 dark:text-neutral-300">Block External API Calls</p>
              <p className="text-[10px] text-neutral-400 dark:text-neutral-500">Prevents api_caller and webhook tools</p>
            </div>
          </div>
        </div>
      </div>

      {/* Budget & Token Limits */}
      <div className="card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Budget & Token Limits</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
              <DollarSign className="h-3 w-3 inline mr-1" />
              Daily Budget Limit (USD)
            </label>
            <input
              type="number"
              className="input"
              min={0}
              step={0.01}
              value={dailyBudget}
              onChange={(e) => setDailyBudget(parseFloat(e.target.value) || 0)}
              placeholder="0 = unlimited"
            />
            <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-1">0 = unlimited spending</p>
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
              <Cpu className="h-3 w-3 inline mr-1" />
              Max Tokens Per Task
            </label>
            <input
              type="number"
              className="input"
              min={0}
              step={1000}
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value) || 0)}
              placeholder="0 = unlimited"
            />
            <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-1">0 = unlimited tokens</p>
          </div>
        </div>
      </div>

      {/* Save */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleSave}
          className="btn-primary flex items-center gap-1.5"
        >
          <Save className="h-3.5 w-3.5" /> Save Safety Settings
        </button>
      </div>
    </div>
  );
}
