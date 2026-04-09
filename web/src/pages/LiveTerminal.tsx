import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Brain,
  Wrench,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  DollarSign,
  Cpu,
  ChevronDown,
  ChevronRight,
  Bot,
  Terminal,
  Activity,
  Hash,
  AlertTriangle,
} from "lucide-react";
import { tasksApi } from "../api/endpoints";
import { cn, formatDate } from "../lib/utils";

// ---------- Types ----------

interface ExecutionStep {
  id: string;
  step: number;
  type: "thinking" | "tool_call" | "result" | "error";
  timestamp: string;
  content: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  tool_result?: string;
  duration?: string;
  status: "running" | "success" | "error" | "pending";
}

// ---------- Demo Data ----------

const DEMO_STEPS: ExecutionStep[] = [
  {
    id: "step-01", step: 1, type: "thinking", timestamp: "2026-04-08T14:00:01Z",
    content: "The user wants me to research competitor pricing in the B2B SaaS market. I should start by searching for recent pricing data and market reports.",
    duration: "0.8s", status: "success",
  },
  {
    id: "step-02", step: 2, type: "tool_call", timestamp: "2026-04-08T14:00:02Z",
    content: "Searching for competitor pricing data",
    tool_name: "web_search", tool_args: { query: "top B2B SaaS competitors pricing 2026", max_results: 15 },
    tool_result: "Found 15 relevant results from Gartner, G2, Capterra, and industry blogs. Top results include pricing pages for Salesforce, HubSpot, Zendesk, Intercom, and Freshworks.",
    duration: "1.2s", status: "success",
  },
  {
    id: "step-03", step: 3, type: "tool_call", timestamp: "2026-04-08T14:00:04Z",
    content: "Navigating to competitor pricing page",
    tool_name: "browser", tool_args: { url: "https://competitor-a.com/pricing", action: "navigate" },
    tool_result: "Page loaded successfully (HTTP 200). Found pricing section with 3 tiers: Starter ($29/mo), Professional ($79/mo), Enterprise (custom).",
    duration: "2.8s", status: "success",
  },
  {
    id: "step-04", step: 4, type: "tool_call", timestamp: "2026-04-08T14:00:07Z",
    content: "Extracting pricing table data",
    tool_name: "web_scraper", tool_args: { selector: ".pricing-table", format: "json", include_features: true },
    tool_result: "Extracted 3 pricing tiers with 24 feature comparisons. Data includes monthly/annual pricing, user limits, and feature availability.",
    duration: "1.5s", status: "success",
  },
  {
    id: "step-05", step: 5, type: "thinking", timestamp: "2026-04-08T14:00:09Z",
    content: "I now have pricing data from the first competitor. Let me continue scraping the remaining 4 competitors before creating the comparison.",
    duration: "0.5s", status: "success",
  },
  {
    id: "step-06", step: 6, type: "tool_call", timestamp: "2026-04-08T14:00:10Z",
    content: "Scraping remaining competitor pricing pages",
    tool_name: "browser", tool_args: { urls: ["competitor-b.com/plans", "competitor-c.com/pricing", "competitor-d.com/plans", "competitor-e.com/pricing"], action: "batch_navigate" },
    tool_result: "All 4 pages loaded. Extracted pricing data for all competitors.",
    duration: "8.4s", status: "success",
  },
  {
    id: "step-07", step: 7, type: "tool_call", timestamp: "2026-04-08T14:00:19Z",
    content: "Analyzing collected pricing data",
    tool_name: "data_analysis", tool_args: { operation: "compare", datasets: 5, metrics: ["price", "features", "value_score"] },
    tool_result: "Analysis complete. Generated value scores, price-to-feature ratios, and competitive positioning matrix for all 5 competitors across 3 tiers.",
    duration: "4.2s", status: "success",
  },
  {
    id: "step-08", step: 8, type: "tool_call", timestamp: "2026-04-08T14:00:24Z",
    content: "Creating comparison spreadsheet",
    tool_name: "excel", tool_args: { action: "create", filename: "competitor_pricing_matrix.xlsx", sheets: ["Overview", "Detailed Comparison", "Feature Matrix"] },
    tool_result: "Created spreadsheet with 3 sheets. Overview contains summary table, Detailed Comparison has per-tier breakdown, Feature Matrix maps 24 features across all competitors.",
    duration: "2.6s", status: "success",
  },
  {
    id: "step-09", step: 9, type: "tool_call", timestamp: "2026-04-08T14:00:27Z",
    content: "Generating visualization charts",
    tool_name: "data_visualization", tool_args: { charts: [{ type: "bar", data: "pricing_comparison" }, { type: "radar", data: "feature_scores" }] },
    tool_result: "Generated 2 charts: price_comparison_chart.png (grouped bar chart) and feature_radar.png (radar chart showing feature coverage).",
    duration: "1.8s", status: "success",
  },
  {
    id: "step-10", step: 10, type: "tool_call", timestamp: "2026-04-08T14:00:29Z",
    content: "Generating PDF analysis report",
    tool_name: "pdf", tool_args: { template: "market_analysis", filename: "competitor_analysis_report.pdf", sections: ["executive_summary", "pricing_breakdown", "recommendations"] },
    tool_result: "Generated 8-page analysis report with executive summary, pricing tables, charts, and strategic recommendations.",
    duration: "5.1s", status: "success",
  },
  {
    id: "step-11", step: 11, type: "tool_call", timestamp: "2026-04-08T14:00:35Z",
    content: "Sending completion notification",
    tool_name: "internal_email", tool_args: { to: "admin@whiteops.local", subject: "Competitor Pricing Analysis Complete", attachments: ["competitor_pricing_matrix.xlsx", "competitor_analysis_report.pdf"] },
    tool_result: "Email sent successfully to admin@whiteops.local with 2 attachments.",
    duration: "0.6s", status: "success",
  },
  {
    id: "step-12", step: 12, type: "result", timestamp: "2026-04-08T14:00:36Z",
    content: "Task completed successfully. Created competitor pricing comparison with 5 competitors across 3 pricing tiers. Deliverables: Excel spreadsheet (competitor_pricing_matrix.xlsx), PDF report (competitor_analysis_report.pdf), and 2 visualization charts. All files sent via email.",
    duration: "0.2s", status: "success",
  },
];

const DEMO_TASK = {
  id: "task-demo-001",
  title: "Competitor Pricing Analysis",
  status: "completed",
  agent_name: "Research Agent",
  agent_id: "agent-001",
  llm_model: "claude-sonnet-4-20250514",
  temperature: 0.7,
  max_iterations: 50,
  current_iteration: 12,
  started_at: "2026-04-08T14:00:00Z",
  completed_at: "2026-04-08T14:00:36Z",
  total_tokens_in: 8450,
  total_tokens_out: 4200,
  total_cost_usd: 0.42,
  tool_calls_count: 9,
  tool_calls_success: 9,
  progress: 100,
};

// ---------- Helpers ----------

const STEP_ICONS: Record<string, React.ReactNode> = {
  thinking: <Brain className="h-4 w-4 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />,
  tool_call: <Wrench className="h-4 w-4 text-neutral-600 dark:text-neutral-400 dark:text-neutral-500" />,
  result: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
  error: <XCircle className="h-4 w-4 text-red-500" />,
};

const STATUS_INDICATOR: Record<string, React.ReactNode> = {
  running: <Loader2 className="h-3.5 w-3.5 text-amber-500 animate-spin" />,
  success: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />,
  error: <XCircle className="h-3.5 w-3.5 text-red-500" />,
  pending: <Clock className="h-3.5 w-3.5 text-neutral-400 dark:text-neutral-500" />,
};

function useElapsedTime(startedAt: string | null, completedAt: string | null) {
  const [elapsed, setElapsed] = useState("0s");

  useEffect(() => {
    if (!startedAt) return;

    const start = new Date(startedAt).getTime();
    if (completedAt) {
      const end = new Date(completedAt).getTime();
      setElapsed(formatDuration(end - start));
      return;
    }

    const interval = setInterval(() => {
      setElapsed(formatDuration(Date.now() - start));
    }, 1000);

    return () => clearInterval(interval);
  }, [startedAt, completedAt]);

  return elapsed;
}

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (minutes < 60) return `${minutes}m ${secs}s`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
}

// ---------- Component ----------

export default function LiveTerminal() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());
  const [steps] = useState<ExecutionStep[]>(DEMO_STEPS);
  const [taskInfo, setTaskInfo] = useState(DEMO_TASK);
  const timelineEndRef = useRef<HTMLDivElement>(null);

  // Try fetching real task data
  const { data: taskData } = useQuery({
    queryKey: ["task-terminal", taskId],
    queryFn: () => tasksApi.get(taskId!),
    enabled: !!taskId,
    refetchInterval: taskInfo.status === "in_progress" ? 2000 : false,
  });

  useEffect(() => {
    if (taskData?.data) {
      const t = taskData.data as any;
      setTaskInfo((prev) => ({
        ...prev,
        id: t.id ?? prev.id,
        title: t.title ?? prev.title,
        status: t.status ?? prev.status,
        started_at: t.started_at ?? prev.started_at,
        completed_at: t.completed_at ?? prev.completed_at,
        progress: t.progress ?? prev.progress,
      }));
    }
  }, [taskData]);

  // Auto-scroll
  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [steps]);

  const elapsed = useElapsedTime(taskInfo.started_at, taskInfo.completed_at);

  const toggleStep = (stepId: string) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(stepId)) next.delete(stepId);
      else next.add(stepId);
      return next;
    });
  };

  const jumpToStep = (stepNum: number) => {
    const el = document.getElementById(`step-${stepNum}`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const statusBadgeClass =
    taskInfo.status === "completed" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" :
    taskInfo.status === "in_progress" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" :
    taskInfo.status === "failed" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" :
    "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400 dark:text-neutral-500";

  return (
    <div>
      {/* Back nav */}
      <button
        onClick={() => navigate(-1)}
        className="btn-ghost flex items-center gap-1.5 mb-4 text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-200"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back
      </button>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center">
            <Terminal className="h-5 w-5 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-neutral-900 dark:text-neutral-100">{taskInfo.title}</h1>
              <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded-full uppercase", statusBadgeClass)}>
                {taskInfo.status.replace("_", " ")}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-xs text-neutral-400 flex items-center gap-1">
                <Bot className="h-3 w-3" /> {taskInfo.agent_name}
              </span>
              <span className="text-xs text-neutral-400 flex items-center gap-1">
                <Clock className="h-3 w-3" /> {elapsed}
              </span>
              <span className="text-xs text-neutral-400 flex items-center gap-1">
                <DollarSign className="h-3 w-3" /> ${taskInfo.total_cost_usd.toFixed(3)}
              </span>
            </div>
          </div>
        </div>

        {/* Jump to step */}
        <select
          className="text-xs bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-600 rounded-lg px-3 py-2 text-neutral-700 dark:text-neutral-300 focus:ring-1 focus:ring-neutral-900 dark:focus:ring-neutral-400 focus:outline-none"
          onChange={(e) => jumpToStep(parseInt(e.target.value))}
          defaultValue=""
        >
          <option value="" disabled>Jump to step...</option>
          {steps.map((s) => (
            <option key={s.id} value={s.step}>
              Step {s.step}: {s.type === "tool_call" ? s.tool_name : s.type}
            </option>
          ))}
        </select>
      </div>

      {/* Main content */}
      <div className="grid grid-cols-10 gap-6">
        {/* Timeline (left 70%) */}
        <div className="col-span-7 space-y-0">
          {steps.map((step, idx) => {
            const isExpanded = expandedSteps.has(step.id);
            const isLast = idx === steps.length - 1;

            return (
              <div key={step.id} id={`step-${step.step}`} className="relative flex gap-4">
                {/* Timeline line */}
                <div className="flex flex-col items-center shrink-0">
                  <div className="w-8 h-8 rounded-full border-2 border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 flex items-center justify-center z-10">
                    {step.status === "running" ? (
                      <Loader2 className="h-4 w-4 text-amber-500 animate-spin" />
                    ) : (
                      STEP_ICONS[step.type]
                    )}
                  </div>
                  {!isLast && (
                    <div className="w-0.5 flex-1 bg-neutral-200 dark:bg-neutral-700 min-h-[16px]" />
                  )}
                </div>

                {/* Step card */}
                <div className="flex-1 pb-4 min-w-0">
                  <div
                    className={cn(
                      "card overflow-hidden transition-shadow",
                      step.status === "running" && "ring-1 ring-amber-400 dark:ring-amber-500"
                    )}
                  >
                    <button
                      onClick={() => toggleStep(step.id)}
                      className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors"
                    >
                      <span className="text-[10px] font-bold text-neutral-400 w-4 shrink-0">#{step.step}</span>
                      <span className="text-xs font-medium text-neutral-900 dark:text-neutral-100 flex-1 truncate">
                        {step.type === "thinking" && "Thinking"}
                        {step.type === "tool_call" && (
                          <span className="flex items-center gap-1.5">
                            <span className="font-mono text-neutral-600 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800 px-1.5 py-0.5 rounded text-[11px]">
                              {step.tool_name}
                            </span>
                            <span className="text-neutral-500 dark:text-neutral-400 font-normal">{step.content}</span>
                          </span>
                        )}
                        {step.type === "result" && "Final Result"}
                        {step.type === "error" && "Error"}
                      </span>
                      {step.duration && (
                        <span className="text-[10px] text-neutral-400 shrink-0">{step.duration}</span>
                      )}
                      {STATUS_INDICATOR[step.status]}
                      {isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5 text-neutral-400 shrink-0" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5 text-neutral-400 shrink-0" />
                      )}
                    </button>

                    {isExpanded && (
                      <div className="px-4 py-3 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 space-y-2">
                        <div className="flex items-center gap-2 text-[10px] text-neutral-400 mb-2">
                          <Clock className="h-3 w-3" />
                          {formatDate(step.timestamp)}
                          {step.duration && (
                            <>
                              <span className="text-neutral-300 dark:text-neutral-600">|</span>
                              Duration: {step.duration}
                            </>
                          )}
                        </div>

                        {step.type === "thinking" && (
                          <p className="text-sm text-neutral-500 dark:text-neutral-400 italic leading-relaxed">
                            {step.content}
                          </p>
                        )}

                        {step.type === "tool_call" && (
                          <>
                            <div>
                              <span className="text-[10px] font-medium text-neutral-400 uppercase">Arguments</span>
                              <pre className="text-[11px] text-neutral-600 dark:text-neutral-400 font-mono mt-1 bg-white dark:bg-neutral-900 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
                                {JSON.stringify(step.tool_args, null, 2)}
                              </pre>
                            </div>
                            {step.tool_result && (
                              <div>
                                <span className="text-[10px] font-medium text-neutral-400 uppercase">Result</span>
                                <pre className="text-[11px] text-neutral-600 dark:text-neutral-400 font-mono mt-1 bg-white dark:bg-neutral-900 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
                                  {step.tool_result}
                                </pre>
                              </div>
                            )}
                          </>
                        )}

                        {step.type === "result" && (
                          <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">
                            {step.content}
                          </p>
                        )}

                        {step.type === "error" && (
                          <div className="flex items-start gap-2 text-sm text-red-600 dark:text-red-400">
                            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                            <p>{step.content}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          <div ref={timelineEndRef} />
        </div>

        {/* Metrics Sidebar (right 30%) */}
        <div className="col-span-3 space-y-4">
          {/* Progress */}
          <div className="card p-4">
            <h3 className="text-xs font-semibold text-neutral-900 dark:text-neutral-100 mb-3 flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-neutral-400 dark:text-neutral-500" /> Progress
            </h3>
            <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2 mb-2">
              <div
                className={cn(
                  "h-2 rounded-full transition-all duration-500",
                  taskInfo.status === "completed" ? "bg-emerald-500" :
                  taskInfo.status === "failed" ? "bg-red-500" :
                  "bg-amber-500"
                )}
                style={{ width: `${taskInfo.progress}%` }}
              />
            </div>
            <p className="text-xs text-neutral-400 text-right">{taskInfo.progress}%</p>
          </div>

          {/* Elapsed Time */}
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="h-3.5 w-3.5 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />
              <span className="text-xs text-neutral-400 dark:text-neutral-500">Elapsed Time</span>
            </div>
            <p className="text-xl font-bold text-neutral-900 dark:text-neutral-100">{elapsed}</p>
          </div>

          {/* Cost */}
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="h-3.5 w-3.5 text-emerald-500" />
              <span className="text-xs text-neutral-400 dark:text-neutral-500">Total Cost</span>
            </div>
            <p className="text-xl font-bold text-neutral-900 dark:text-neutral-100">${taskInfo.total_cost_usd.toFixed(4)}</p>
          </div>

          {/* Tokens */}
          <div className="card p-4">
            <h3 className="text-xs font-semibold text-neutral-900 dark:text-neutral-100 mb-3 flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5 text-neutral-400 dark:text-neutral-500" /> Tokens
            </h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-neutral-400 dark:text-neutral-500">Input</span>
                <span className="text-xs font-mono font-medium text-neutral-700 dark:text-neutral-300">
                  {taskInfo.total_tokens_in.toLocaleString()}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-neutral-400 dark:text-neutral-500">Output</span>
                <span className="text-xs font-mono font-medium text-neutral-700 dark:text-neutral-300">
                  {taskInfo.total_tokens_out.toLocaleString()}
                </span>
              </div>
              <div className="flex items-center justify-between pt-1 border-t border-neutral-200 dark:border-neutral-700">
                <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">Total</span>
                <span className="text-xs font-mono font-bold text-neutral-900 dark:text-neutral-100">
                  {(taskInfo.total_tokens_in + taskInfo.total_tokens_out).toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          {/* Tool Calls */}
          <div className="card p-4">
            <h3 className="text-xs font-semibold text-neutral-900 dark:text-neutral-100 mb-3 flex items-center gap-1.5">
              <Wrench className="h-3.5 w-3.5 text-neutral-400 dark:text-neutral-500" /> Tool Calls
            </h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-neutral-400 dark:text-neutral-500">Total</span>
                <span className="text-xs font-bold text-neutral-900 dark:text-neutral-100">{taskInfo.tool_calls_count}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-neutral-400 dark:text-neutral-500">Success Rate</span>
                <span className="text-xs font-bold text-emerald-600">
                  {taskInfo.tool_calls_count > 0
                    ? ((taskInfo.tool_calls_success / taskInfo.tool_calls_count) * 100).toFixed(0)
                    : 0}%
                </span>
              </div>
            </div>
          </div>

          {/* Iteration */}
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-1">
              <Hash className="h-3.5 w-3.5 text-neutral-400 dark:text-neutral-500" />
              <span className="text-xs text-neutral-400 dark:text-neutral-500">Iteration</span>
            </div>
            <p className="text-sm font-bold text-neutral-900 dark:text-neutral-100">
              {taskInfo.current_iteration} <span className="text-neutral-400 font-normal">of {taskInfo.max_iterations}</span>
            </p>
          </div>

          {/* Agent Info */}
          <div className="card p-4">
            <h3 className="text-xs font-semibold text-neutral-900 dark:text-neutral-100 mb-3 flex items-center gap-1.5">
              <Bot className="h-3.5 w-3.5 text-neutral-400 dark:text-neutral-500" /> Agent
            </h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-neutral-400 dark:text-neutral-500">Name</span>
                <span className="text-xs font-medium text-neutral-700 dark:text-neutral-300">{taskInfo.agent_name}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-neutral-400 dark:text-neutral-500">Model</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">
                  {taskInfo.llm_model}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-neutral-400 dark:text-neutral-500">Temperature</span>
                <span className="text-xs font-medium text-neutral-700 dark:text-neutral-300">{taskInfo.temperature}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
