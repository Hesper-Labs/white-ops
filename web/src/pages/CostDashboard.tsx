import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  DollarSign,
  TrendingDown,
  Wallet,
  Bot,
  AlertTriangle,
  Calendar,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { costApi } from "../api/endpoints";
import { cn } from "../lib/utils";

// --- Demo Data ---

const DEMO_DAILY_COSTS = Array.from({ length: 30 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (29 - i));
  return {
    date: d.toISOString().slice(0, 10),
    cost: +(Math.random() * 40 + 15).toFixed(2),
  };
});

const DEMO_AGENT_COSTS = [
  { id: "a1", name: "Research Agent", provider: "Anthropic", model: "claude-sonnet-4-20250514", tokens_used: 1_245_300, cost: 87.42 },
  { id: "a2", name: "Report Writer", provider: "OpenAI", model: "gpt-4o", tokens_used: 892_100, cost: 62.18 },
  { id: "a3", name: "Code Reviewer", provider: "Anthropic", model: "claude-sonnet-4-20250514", tokens_used: 534_200, cost: 38.90 },
  { id: "a4", name: "Data Analyst", provider: "OpenAI", model: "gpt-4o-mini", tokens_used: 2_103_400, cost: 24.55 },
  { id: "a5", name: "HR Coordinator", provider: "Anthropic", model: "claude-haiku", tokens_used: 1_890_000, cost: 12.30 },
  { id: "a6", name: "Customer Support", provider: "Google", model: "gemini-pro", tokens_used: 678_500, cost: 9.85 },
];

const DEMO_PROVIDER_COSTS = [
  { name: "Anthropic", value: 138.62, color: "#6366f1" },
  { name: "OpenAI", value: 86.73, color: "#10b981" },
  { name: "Google", value: 9.85, color: "#f59e0b" },
];

const DEMO_BUDGET = { monthly_budget: 500, current_spend: 235.20, daily_average: 7.84 };

const DEMO_ALERTS = [
  { id: "ba1", level: "warning", message: "Anthropic spend at 83% of weekly allocation ($138 / $166)", created_at: "2025-04-05T09:00:00Z" },
  { id: "ba2", level: "info", message: "Daily cost trending 12% lower than last week", created_at: "2025-04-04T18:00:00Z" },
  { id: "ba3", level: "critical", message: "GPT-4o token usage exceeded daily cap by 15%", created_at: "2025-04-03T14:30:00Z" },
];

// --- Component ---

export default function CostDashboard() {
  const [dateRange, setDateRange] = useState<"7d" | "14d" | "30d">("30d");

  const { data: costData } = useQuery({
    queryKey: ["costs", dateRange],
    queryFn: async () => {
      try {
        const res = await costApi.getSummary();
        return res.data;
      } catch {
        return null;
      }
    },
    refetchInterval: 30000,
  });

  const budget = costData?.budget ?? DEMO_BUDGET;
  const dailyCosts = costData?.daily_costs ?? DEMO_DAILY_COSTS;
  const agentCosts = costData?.agent_costs ?? DEMO_AGENT_COSTS;
  const providerCosts = costData?.provider_costs ?? DEMO_PROVIDER_COSTS;
  const alerts = costData?.alerts ?? DEMO_ALERTS;

  const filteredDaily = useMemo(() => {
    const days = dateRange === "7d" ? 7 : dateRange === "14d" ? 14 : 30;
    return dailyCosts.slice(-days);
  }, [dailyCosts, dateRange]);

  const totalSpend = agentCosts.reduce((s: number, a: any) => s + a.cost, 0);
  const budgetPercent = ((budget.current_spend / budget.monthly_budget) * 100).toFixed(1);
  const budgetRemaining = budget.monthly_budget - budget.current_spend;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-neutral-900 dark:text-white">Cost Dashboard</h1>
          <p className="text-xs text-neutral-400 mt-0.5">Track spending and manage budgets across providers</p>
        </div>
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-neutral-400 dark:text-neutral-500" />
          {(["7d", "14d", "30d"] as const).map((r) => (
            <button
              key={r}
              onClick={() => setDateRange(r)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-sm",
                dateRange === r
                  ? "bg-neutral-900 text-white"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
              )}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="card p-5">
          <div className="flex items-center gap-2 text-neutral-500 mb-2">
            <DollarSign className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Total Spend</span>
          </div>
          <p className="text-3xl font-bold">${totalSpend.toFixed(2)}</p>
          <p className="text-xs text-neutral-400 mt-1">this month</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 text-neutral-500 mb-2">
            <TrendingDown className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Daily Average</span>
          </div>
          <p className="text-3xl font-bold">${budget.daily_average.toFixed(2)}</p>
          <p className="text-xs text-neutral-400 mt-1">per day</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 text-neutral-500 mb-2">
            <Wallet className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Budget Remaining</span>
          </div>
          <p className={cn("text-3xl font-bold", budgetRemaining < 50 ? "text-red-600" : "text-green-600")}>
            ${budgetRemaining.toFixed(2)}
          </p>
          <p className="text-xs text-neutral-400 mt-1">{budgetPercent}% used</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 text-neutral-500 mb-2">
            <Bot className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Active Agents Cost</span>
          </div>
          <p className="text-3xl font-bold">{agentCosts.length}</p>
          <p className="text-xs text-neutral-400 mt-1">agents incurring cost</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Area Chart */}
        <div className="card p-6 lg:col-span-2">
          <h2 className="text-sm font-semibold text-neutral-900 mb-4">Daily Cost Trend</h2>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={filteredDaily}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v: string) => v.slice(5)} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `$${v}`} />
              <Tooltip formatter={(v: number) => [`$${v.toFixed(2)}`, "Cost"]} />
              <Area type="monotone" dataKey="cost" stroke="#6366f1" fill="#6366f1" fillOpacity={0.1} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Pie Chart */}
        <div className="card p-6">
          <h2 className="text-sm font-semibold text-neutral-900 mb-4">Cost by Provider</h2>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={providerCosts} cx="50%" cy="45%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                {providerCosts.map((entry: any, i: number) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Legend verticalAlign="bottom" height={36} formatter={(value: string) => <span className="text-xs text-neutral-600">{value}</span>} />
              <Tooltip formatter={(v: number) => `$${v.toFixed(2)}`} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Budget Alerts & Agent Costs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Budget Alerts */}
        <div className="card p-6">
          <h2 className="text-sm font-semibold text-neutral-900 mb-4">Budget Alerts</h2>
          {alerts.length === 0 ? (
            <p className="text-xs text-neutral-400 dark:text-neutral-500">No alerts</p>
          ) : (
            <div className="space-y-3">
              {alerts.map((alert: any) => (
                <div
                  key={alert.id}
                  className={cn(
                    "flex items-start gap-2 p-3 rounded-lg text-xs",
                    alert.level === "critical" ? "bg-red-50 text-red-700" :
                    alert.level === "warning" ? "bg-amber-50 text-amber-700" :
                    "bg-neutral-100 text-neutral-700 dark:text-neutral-300"
                  )}
                >
                  <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                  <div>
                    <p>{alert.message}</p>
                    <p className="text-[10px] opacity-60 mt-1">
                      {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Agent Cost Table */}
        <div className="card overflow-hidden lg:col-span-2">
          <div className="px-6 py-4 border-b border-neutral-100">
            <h2 className="text-sm font-semibold text-neutral-900 dark:text-white">Cost Breakdown by Agent</h2>
          </div>
          <table className="w-full">
            <thead>
              <tr>
                <th className="table-header">Agent</th>
                <th className="table-header">Provider</th>
                <th className="table-header">Model</th>
                <th className="table-header text-right">Tokens Used</th>
                <th className="table-header text-right">Cost</th>
              </tr>
            </thead>
            <tbody>
              {agentCosts.map((agent: any) => (
                <tr key={agent.id} className="border-b border-neutral-100 hover:bg-neutral-50 dark:bg-neutral-800/50">
                  <td className="px-4 py-3 text-xs font-medium text-neutral-900 dark:text-white">{agent.name}</td>
                  <td className="px-4 py-3">
                    <span className={cn(
                      "text-[10px] font-semibold px-2 py-0.5 rounded-full",
                      agent.provider === "Anthropic" ? "bg-indigo-100 text-indigo-700" :
                      agent.provider === "OpenAI" ? "bg-emerald-100 text-emerald-700" :
                      "bg-amber-100 text-amber-700"
                    )}>
                      {agent.provider}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-neutral-500 font-mono">{agent.model}</td>
                  <td className="px-4 py-3 text-xs text-neutral-600 text-right">
                    {(agent.tokens_used as number).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-xs font-semibold text-neutral-900 text-right">
                    ${(agent.cost as number).toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="bg-neutral-50 dark:bg-neutral-800/50">
                <td colSpan={4} className="px-4 py-3 text-xs font-semibold text-neutral-700 dark:text-neutral-300">Total</td>
                <td className="px-4 py-3 text-xs font-bold text-neutral-900 text-right">${totalSpend.toFixed(2)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Budget Progress Bar */}
      <div className="card p-6 mt-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-neutral-900 dark:text-white">Monthly Budget Progress</h2>
          <span className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">${budget.current_spend.toFixed(2)} / ${budget.monthly_budget.toFixed(2)}</span>
        </div>
        <div className="w-full bg-neutral-100 rounded-full h-3">
          <div
            className={cn(
              "rounded-full h-3 transition-all",
              parseFloat(budgetPercent) > 90 ? "bg-red-500" :
              parseFloat(budgetPercent) > 80 ? "bg-amber-500" :
              "bg-green-500"
            )}
            style={{ width: `${Math.min(parseFloat(budgetPercent), 100)}%` }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-neutral-400 dark:text-neutral-500">0%</span>
          <span className={cn(
            "text-[10px] font-medium",
            parseFloat(budgetPercent) > 90 ? "text-red-600" :
            parseFloat(budgetPercent) > 80 ? "text-amber-600" :
            "text-green-600"
          )}>
            {budgetPercent}%
          </span>
          <span className="text-[10px] text-neutral-400 dark:text-neutral-500">100%</span>
        </div>
      </div>
    </div>
  );
}
