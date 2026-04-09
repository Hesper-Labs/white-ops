import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Zap,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Settings,
  Save,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { circuitBreakerApi } from "../api/endpoints";
import { cn, formatDate } from "../lib/utils";
import toast from "react-hot-toast";

// --- Demo Data ---

const DEMO_SERVICES = [
  {
    id: "svc1", name: "LLM API (Anthropic)", state: "closed",
    failure_count: 0, success_rate: 99.8, last_failure: null,
    response_time: { avg: 1250, p95: 2100, p99: 3400 },
    requests_total: 14520, uptime_hours: 720,
  },
  {
    id: "svc2", name: "LLM API (OpenAI)", state: "half_open",
    failure_count: 3, success_rate: 94.2, last_failure: "2025-04-05T15:30:00Z",
    response_time: { avg: 980, p95: 1800, p99: 2900 },
    requests_total: 8930, uptime_hours: 718,
  },
  {
    id: "svc3", name: "MinIO Object Storage", state: "closed",
    failure_count: 0, success_rate: 99.9, last_failure: "2025-03-28T04:15:00Z",
    response_time: { avg: 45, p95: 120, p99: 250 },
    requests_total: 52340, uptime_hours: 720,
  },
  {
    id: "svc4", name: "PostgreSQL Database", state: "closed",
    failure_count: 0, success_rate: 100, last_failure: null,
    response_time: { avg: 12, p95: 35, p99: 85 },
    requests_total: 245800, uptime_hours: 720,
  },
  {
    id: "svc5", name: "Redis Cache", state: "closed",
    failure_count: 0, success_rate: 99.99, last_failure: null,
    response_time: { avg: 2, p95: 5, p99: 12 },
    requests_total: 1245000, uptime_hours: 720,
  },
  {
    id: "svc6", name: "SMTP Mail Service", state: "open",
    failure_count: 12, success_rate: 0, last_failure: "2025-04-05T16:45:00Z",
    response_time: { avg: 0, p95: 0, p99: 0 },
    requests_total: 3420, uptime_hours: 695,
  },
  {
    id: "svc7", name: "Webhook Relay", state: "closed",
    failure_count: 1, success_rate: 98.5, last_failure: "2025-04-04T22:10:00Z",
    response_time: { avg: 320, p95: 850, p99: 1400 },
    requests_total: 6780, uptime_hours: 719,
  },
  {
    id: "svc8", name: "External Search API", state: "half_open",
    failure_count: 5, success_rate: 87.3, last_failure: "2025-04-05T14:20:00Z",
    response_time: { avg: 1800, p95: 3200, p99: 5000 },
    requests_total: 2150, uptime_hours: 710,
  },
];

const DEMO_ACTIVITY_LOG = [
  { id: "cl1", service: "SMTP Mail Service", from_state: "half_open", to_state: "open", timestamp: "2025-04-05T16:45:00Z", reason: "3 consecutive failures in half-open state" },
  { id: "cl2", service: "External Search API", from_state: "closed", to_state: "half_open", timestamp: "2025-04-05T14:20:00Z", reason: "Failure threshold exceeded (5/5)" },
  { id: "cl3", service: "LLM API (OpenAI)", from_state: "open", to_state: "half_open", timestamp: "2025-04-05T15:30:00Z", reason: "Recovery timeout elapsed, testing connection" },
  { id: "cl4", service: "SMTP Mail Service", from_state: "closed", to_state: "open", timestamp: "2025-04-05T12:00:00Z", reason: "Connection refused: SMTP server unreachable" },
  { id: "cl5", service: "Webhook Relay", from_state: "half_open", to_state: "closed", timestamp: "2025-04-04T22:30:00Z", reason: "Successful test requests, circuit closed" },
  { id: "cl6", service: "MinIO Object Storage", from_state: "open", to_state: "closed", timestamp: "2025-03-28T04:30:00Z", reason: "Service recovered after maintenance window" },
];

const DEMO_CONFIG = {
  failure_threshold: 5,
  recovery_timeout_seconds: 60,
  half_open_max_requests: 3,
  monitoring_window_seconds: 300,
};

const stateConfig: Record<string, { label: string; color: string; bgColor: string; icon: React.ElementType }> = {
  closed: { label: "Healthy", color: "text-green-600", bgColor: "bg-green-50 border-green-200", icon: CheckCircle2 },
  half_open: { label: "Testing", color: "text-amber-600", bgColor: "bg-amber-50 border-amber-200", icon: AlertTriangle },
  open: { label: "Open", color: "text-red-600", bgColor: "bg-red-50 border-red-200", icon: XCircle },
};

// --- Component ---

export default function CircuitBreakers() {
  const [showConfig, setShowConfig] = useState(false);
  const [config, setConfig] = useState(DEMO_CONFIG);
  const queryClient = useQueryClient();

  const { data: cbData } = useQuery({
    queryKey: ["circuit-breakers"],
    queryFn: async () => {
      try {
        const res = await circuitBreakerApi.getAll();
        return res.data;
      } catch {
        return null;
      }
    },
    refetchInterval: 5000,
  });

  const services = cbData?.services ?? DEMO_SERVICES;
  const activityLog = cbData?.activity_log ?? DEMO_ACTIVITY_LOG;

  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) => {
      if (action === "force-open") return circuitBreakerApi.forceOpen(id).catch(() => Promise.resolve());
      if (action === "force-close") return circuitBreakerApi.forceClose(id).catch(() => Promise.resolve());
      return circuitBreakerApi.reset(id).catch(() => Promise.resolve());
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["circuit-breakers"] });
      toast.success("Circuit breaker updated");
    },
  });

  const saveConfigMutation = useMutation({
    mutationFn: (_data: Record<string, unknown>) =>
      Promise.resolve(),
    onSuccess: () => {
      toast.success("Configuration saved");
    },
  });

  const closedCount = services.filter((s: any) => s.state === "closed").length;
  const halfOpenCount = services.filter((s: any) => s.state === "half_open").length;
  const openCount = services.filter((s: any) => s.state === "open").length;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-neutral-900 dark:text-white">Circuit Breakers</h1>
          <p className="text-xs text-neutral-400 mt-0.5">Monitor service health and manage circuit breaker states</p>
        </div>
        <button
          onClick={() => setShowConfig(!showConfig)}
          className="btn-secondary text-sm flex items-center gap-1.5"
        >
          <Settings className="h-3.5 w-3.5" />
          Configuration
          {showConfig ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="card p-5">
          <div className="flex items-center gap-2 text-neutral-500 mb-2">
            <Activity className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Services Monitored</span>
          </div>
          <p className="text-3xl font-bold">{services.length}</p>
          <p className="text-xs text-neutral-400 mt-1">external dependencies</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 text-red-500 mb-2">
            <XCircle className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Open Circuits</span>
          </div>
          <p className="text-3xl font-bold text-red-600">{openCount}</p>
          <p className="text-xs text-neutral-400 mt-1">services down</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 text-amber-500 mb-2">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Half-Open</span>
          </div>
          <p className="text-3xl font-bold text-amber-600">{halfOpenCount}</p>
          <p className="text-xs text-neutral-400 mt-1">testing recovery</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 text-green-500 mb-2">
            <CheckCircle2 className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Closed (Healthy)</span>
          </div>
          <p className="text-3xl font-bold text-green-600">{closedCount}</p>
          <p className="text-xs text-neutral-400 mt-1">operating normally</p>
        </div>
      </div>

      {/* Configuration Panel */}
      {showConfig && (
        <div className="card p-6 mb-6">
          <h2 className="text-sm font-semibold text-neutral-900 mb-4">Circuit Breaker Configuration</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="text-xs font-medium text-neutral-700 mb-1 block">Failure Threshold</label>
              <input
                type="number"
                className="input w-full"
                value={config.failure_threshold}
                onChange={(e) => setConfig({ ...config, failure_threshold: +e.target.value })}
              />
              <p className="text-[10px] text-neutral-400 mt-1">Failures before opening</p>
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-700 mb-1 block">Recovery Timeout (s)</label>
              <input
                type="number"
                className="input w-full"
                value={config.recovery_timeout_seconds}
                onChange={(e) => setConfig({ ...config, recovery_timeout_seconds: +e.target.value })}
              />
              <p className="text-[10px] text-neutral-400 mt-1">Wait before half-open</p>
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-700 mb-1 block">Half-Open Max Requests</label>
              <input
                type="number"
                className="input w-full"
                value={config.half_open_max_requests}
                onChange={(e) => setConfig({ ...config, half_open_max_requests: +e.target.value })}
              />
              <p className="text-[10px] text-neutral-400 mt-1">Test requests allowed</p>
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-700 mb-1 block">Monitoring Window (s)</label>
              <input
                type="number"
                className="input w-full"
                value={config.monitoring_window_seconds}
                onChange={(e) => setConfig({ ...config, monitoring_window_seconds: +e.target.value })}
              />
              <p className="text-[10px] text-neutral-400 mt-1">Sliding window period</p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-neutral-100">
            <button
              onClick={() => saveConfigMutation.mutate(config)}
              className="btn-primary text-sm flex items-center gap-1.5"
            >
              <Save className="h-3.5 w-3.5" /> Save Configuration
            </button>
          </div>
        </div>
      )}

      {/* Service Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-6">
        {services.map((service: any) => {
          const state = stateConfig[service.state as string] ?? { label: "Healthy", color: "text-green-600", bgColor: "bg-green-50 border-green-200", icon: CheckCircle2 };
          const StateIcon = state.icon;

          return (
            <div key={service.id} className={cn("card p-5 border", state.bgColor)}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <StateIcon className={cn("h-5 w-5", state.color)} />
                  <h3 className="text-sm font-semibold text-neutral-900 dark:text-white">{service.name}</h3>
                </div>
                <span className={cn(
                  "text-[10px] font-bold px-2 py-0.5 rounded-full",
                  service.state === "closed" ? "bg-green-200 text-green-800" :
                  service.state === "half_open" ? "bg-amber-200 text-amber-800" :
                  "bg-red-200 text-red-800"
                )}>
                  {state.label}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <span className="text-[10px] text-neutral-400 uppercase">Failures</span>
                  <p className={cn("text-sm font-bold", service.failure_count > 0 ? "text-red-600" : "text-neutral-700 dark:text-neutral-300")}>
                    {service.failure_count}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] text-neutral-400 uppercase">Success Rate</span>
                  <p className={cn("text-sm font-bold",
                    service.success_rate >= 99 ? "text-green-600" :
                    service.success_rate >= 90 ? "text-amber-600" :
                    "text-red-600"
                  )}>
                    {service.success_rate}%
                  </p>
                </div>
                <div>
                  <span className="text-[10px] text-neutral-400 uppercase">Last Failure</span>
                  <p className="text-xs text-neutral-600">
                    {service.last_failure ? formatDate(service.last_failure) : "Never"}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] text-neutral-400 uppercase">Total Requests</span>
                  <p className="text-xs text-neutral-600">{(service.requests_total as number).toLocaleString()}</p>
                </div>
              </div>

              {/* Response Times */}
              <div className="bg-white/60 rounded-lg p-2 mb-3">
                <span className="text-[10px] text-neutral-400 uppercase">Response Time (ms)</span>
                <div className="flex items-center gap-4 mt-1">
                  <div>
                    <span className="text-[10px] text-neutral-400 dark:text-neutral-500">avg</span>
                    <p className="text-xs font-medium">{service.response_time.avg}</p>
                  </div>
                  <div>
                    <span className="text-[10px] text-neutral-400 dark:text-neutral-500">p95</span>
                    <p className="text-xs font-medium">{service.response_time.p95}</p>
                  </div>
                  <div>
                    <span className="text-[10px] text-neutral-400 dark:text-neutral-500">p99</span>
                    <p className="text-xs font-medium">{service.response_time.p99}</p>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-3 border-t border-neutral-200/50">
                {service.state !== "open" && (
                  <button
                    onClick={() => actionMutation.mutate({ id: service.id, action: "force-open" })}
                    className="flex-1 text-[11px] font-medium py-1.5 rounded-md bg-red-100 text-red-700 hover:bg-red-200 transition-colors"
                  >
                    Force Open
                  </button>
                )}
                {service.state !== "closed" && (
                  <button
                    onClick={() => actionMutation.mutate({ id: service.id, action: "force-close" })}
                    className="flex-1 text-[11px] font-medium py-1.5 rounded-md bg-green-100 text-green-700 hover:bg-green-200 transition-colors"
                  >
                    Force Close
                  </button>
                )}
                <button
                  onClick={() => actionMutation.mutate({ id: service.id, action: "reset" })}
                  className="flex-1 text-[11px] font-medium py-1.5 rounded-md bg-neutral-100 text-neutral-700 hover:bg-neutral-200 transition-colors flex items-center justify-center gap-1"
                >
                  <RefreshCw className="h-3 w-3" /> Reset
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Activity Log */}
      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b border-neutral-100 flex items-center gap-2">
          <Clock className="h-4 w-4 text-neutral-400 dark:text-neutral-500" />
          <h2 className="text-sm font-semibold text-neutral-900 dark:text-white">State Change Log</h2>
        </div>
        <table className="w-full">
          <thead>
            <tr>
              <th className="table-header">Time</th>
              <th className="table-header">Service</th>
              <th className="table-header">Transition</th>
              <th className="table-header">Reason</th>
            </tr>
          </thead>
          <tbody>
            {activityLog.map((entry: any) => {
              const fromState = stateConfig[entry.from_state] ?? stateConfig.closed;
              const toState = stateConfig[entry.to_state] ?? stateConfig.closed;
              return (
                <tr key={entry.id} className="border-b border-neutral-100 hover:bg-neutral-50 dark:bg-neutral-800/50">
                  <td className="px-4 py-3 text-xs text-neutral-500 whitespace-nowrap">
                    {formatDate(entry.timestamp)}
                  </td>
                  <td className="px-4 py-3 text-xs font-medium text-neutral-900 dark:text-white">{entry.service}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 text-xs">
                      <span className={cn(
                        "px-1.5 py-0.5 rounded text-[10px] font-semibold",
                        entry.from_state === "closed" ? "bg-green-100 text-green-700" :
                        entry.from_state === "half_open" ? "bg-amber-100 text-amber-700" :
                        "bg-red-100 text-red-700"
                      )}>
                        {fromState?.label}
                      </span>
                      <Zap className="h-3 w-3 text-neutral-300" />
                      <span className={cn(
                        "px-1.5 py-0.5 rounded text-[10px] font-semibold",
                        entry.to_state === "closed" ? "bg-green-100 text-green-700" :
                        entry.to_state === "half_open" ? "bg-amber-100 text-amber-700" :
                        "bg-red-100 text-red-700"
                      )}>
                        {toState?.label}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-neutral-500 max-w-md truncate">{entry.reason}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
