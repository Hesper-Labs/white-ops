import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  RefreshCw,
  Trash2,
  Eye,
  X,
  Clock,
  CheckCircle2,
  XCircle,
  Filter,
} from "lucide-react";
import { deadLetterApi } from "../api/endpoints";
import { cn, formatDate } from "../lib/utils";
import toast from "react-hot-toast";

// --- Demo Data ---

const DEMO_FAILED_TASKS = [
  {
    id: "dlq1", task_title: "Generate Q1 Financial Report", agent_name: "Report Writer",
    error_message: "LLM API timeout after 30s", error_type: "TimeoutError",
    failed_at: "2025-04-05T14:22:00Z", retry_count: 2, max_retries: 3, status: "pending_retry",
    stack_trace: "TimeoutError: Request timed out after 30000ms\n  at LLMClient.complete (llm/client.ts:142)\n  at Agent.execute (agents/base.ts:89)\n  at TaskRunner.run (runner/task.ts:56)",
    metadata: { task_id: "t12", priority: "high", created_at: "2025-04-05T10:00:00Z", estimated_tokens: 45000 },
    execution_history: [
      { attempt: 1, started_at: "2025-04-05T10:05:00Z", failed_at: "2025-04-05T10:05:32Z", error: "TimeoutError" },
      { attempt: 2, started_at: "2025-04-05T12:10:00Z", failed_at: "2025-04-05T12:10:31Z", error: "TimeoutError" },
    ],
  },
  {
    id: "dlq2", task_title: "Parse Customer Feedback CSV", agent_name: "Data Analyst",
    error_message: "Invalid CSV format: unexpected delimiter at row 1432", error_type: "ParseError",
    failed_at: "2025-04-05T11:45:00Z", retry_count: 1, max_retries: 3, status: "pending_retry",
    stack_trace: "ParseError: Invalid CSV format\n  at CSVParser.parse (parsers/csv.ts:78)\n  at FileProcessor.process (processors/file.ts:34)",
    metadata: { task_id: "t15", priority: "medium", created_at: "2025-04-05T09:30:00Z", file_name: "feedback_q1.csv" },
    execution_history: [
      { attempt: 1, started_at: "2025-04-05T09:35:00Z", failed_at: "2025-04-05T09:35:12Z", error: "ParseError" },
    ],
  },
  {
    id: "dlq3", task_title: "Send Weekly Digest Email", agent_name: "HR Coordinator",
    error_message: "SMTP connection refused: mail.company.com:587", error_type: "ConnectionError",
    failed_at: "2025-04-04T08:00:00Z", retry_count: 3, max_retries: 3, status: "permanently_failed",
    stack_trace: "ConnectionError: SMTP connection refused\n  at SMTPClient.connect (mail/smtp.ts:45)\n  at MailService.send (services/mail.ts:22)",
    metadata: { task_id: "t08", priority: "low", created_at: "2025-04-03T22:00:00Z", recipients: 24 },
    execution_history: [
      { attempt: 1, started_at: "2025-04-04T06:00:00Z", failed_at: "2025-04-04T06:00:05Z", error: "ConnectionError" },
      { attempt: 2, started_at: "2025-04-04T07:00:00Z", failed_at: "2025-04-04T07:00:04Z", error: "ConnectionError" },
      { attempt: 3, started_at: "2025-04-04T08:00:00Z", failed_at: "2025-04-04T08:00:03Z", error: "ConnectionError" },
    ],
  },
  {
    id: "dlq4", task_title: "Summarize Meeting Transcript", agent_name: "Research Agent",
    error_message: "Token limit exceeded: input 128,500 tokens (max 100,000)", error_type: "TokenLimitError",
    failed_at: "2025-04-05T16:10:00Z", retry_count: 0, max_retries: 3, status: "pending_retry",
    stack_trace: "TokenLimitError: Input exceeds maximum context\n  at Tokenizer.validate (llm/tokenizer.ts:67)\n  at Agent.prepare (agents/base.ts:55)",
    metadata: { task_id: "t18", priority: "high", created_at: "2025-04-05T15:00:00Z", transcript_length: "3h 20m" },
    execution_history: [],
  },
  {
    id: "dlq5", task_title: "Deploy Staging Environment", agent_name: "Code Reviewer",
    error_message: "Docker build failed: npm ERR! Missing peer dependency", error_type: "BuildError",
    failed_at: "2025-04-05T13:30:00Z", retry_count: 3, max_retries: 3, status: "permanently_failed",
    stack_trace: "BuildError: Docker build failed at step 7/12\n  npm ERR! peer dep missing: react@^18, required by react-dom@19.0.0\n  at DockerBuilder.build (deploy/docker.ts:112)\n  at DeployService.staging (services/deploy.ts:44)",
    metadata: { task_id: "t20", priority: "critical", created_at: "2025-04-05T10:00:00Z", branch: "feature/new-ui" },
    execution_history: [
      { attempt: 1, started_at: "2025-04-05T10:30:00Z", failed_at: "2025-04-05T10:32:00Z", error: "BuildError" },
      { attempt: 2, started_at: "2025-04-05T11:30:00Z", failed_at: "2025-04-05T11:32:15Z", error: "BuildError" },
      { attempt: 3, started_at: "2025-04-05T13:28:00Z", failed_at: "2025-04-05T13:30:00Z", error: "BuildError" },
    ],
  },
];

// --- Component ---

export default function DeadLetterQueue() {
  const [selectedTask, setSelectedTask] = useState<any>(null);
  const [filterType, setFilterType] = useState("");
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["dead-letter-queue"],
    queryFn: async () => {
      try {
        const res = await deadLetterApi.getAll();
        return res.data;
      } catch {
        return DEMO_FAILED_TASKS;
      }
    },
    refetchInterval: 10000,
  });

  const tasks = (Array.isArray(data) ? data : data?.data ?? DEMO_FAILED_TASKS) as any[];

  const retryMutation = useMutation({
    mutationFn: (id: string) => deadLetterApi.retry(id).catch(() => Promise.resolve()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dead-letter-queue"] });
      toast.success("Task queued for retry");
    },
  });

  const discardMutation = useMutation({
    mutationFn: (id: string) => deadLetterApi.discard(id).catch(() => Promise.resolve()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dead-letter-queue"] });
      toast.success("Task discarded");
    },
  });

  const bulkRetry = () => {
    const retryable = tasks.filter((t: any) => t.status === "pending_retry");
    retryable.forEach((t: any) => retryMutation.mutate(t.id));
    toast.success(`${retryable.length} tasks queued for retry`);
  };

  const bulkDiscard = () => {
    tasks.forEach((t: any) => discardMutation.mutate(t.id));
    toast.success("All tasks discarded");
  };

  const filtered = filterType
    ? tasks.filter((t: any) => t.error_type === filterType)
    : tasks;

  const errorTypes = [...new Set(tasks.map((t: any) => t.error_type))];
  const pendingRetry = tasks.filter((t: any) => t.status === "pending_retry").length;
  const permFailed = tasks.filter((t: any) => t.status === "permanently_failed").length;
  const retriedToday = tasks.reduce((s: number, t: any) => {
    const today = new Date().toISOString().slice(0, 10);
    const attempts = (t.execution_history ?? []).filter(
      (h: any) => h.started_at?.slice(0, 10) === today
    ).length;
    return s + attempts;
  }, 0);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-neutral-900 dark:text-white">Dead Letter Queue</h1>
          <p className="text-xs text-neutral-400 mt-0.5">Inspect failed tasks and manage retries</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={bulkRetry} className="btn-primary text-sm flex items-center gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" /> Retry All
          </button>
          <button onClick={bulkDiscard} className="btn-danger text-sm flex items-center gap-1.5">
            <Trash2 className="h-3.5 w-3.5" /> Discard All
          </button>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="card p-5">
          <div className="flex items-center gap-2 text-neutral-500 mb-2">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Total Failed</span>
          </div>
          <p className="text-3xl font-bold text-red-600">{tasks.length}</p>
          <p className="text-xs text-neutral-400 mt-1">tasks in queue</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 text-neutral-500 mb-2">
            <Clock className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Pending Retry</span>
          </div>
          <p className="text-3xl font-bold text-amber-600">{pendingRetry}</p>
          <p className="text-xs text-neutral-400 mt-1">awaiting retry</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 text-neutral-500 mb-2">
            <RefreshCw className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Retried Today</span>
          </div>
          <p className="text-3xl font-bold">{retriedToday}</p>
          <p className="text-xs text-neutral-400 mt-1">attempts today</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 text-neutral-500 mb-2">
            <XCircle className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Permanently Failed</span>
          </div>
          <p className="text-3xl font-bold text-neutral-600">{permFailed}</p>
          <p className="text-xs text-neutral-400 mt-1">max retries reached</p>
        </div>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2 mb-4">
        <Filter className="h-4 w-4 text-neutral-400 dark:text-neutral-500" />
        <select
          className="input w-48"
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
        >
          <option value="">All Error Types</option>
          {errorTypes.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr>
              <th className="table-header">Task</th>
              <th className="table-header">Agent</th>
              <th className="table-header">Error</th>
              <th className="table-header">Failed At</th>
              <th className="table-header text-center">Retries</th>
              <th className="table-header">Status</th>
              <th className="table-header text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center">
                  <CheckCircle2 className="h-10 w-10 text-green-300 mx-auto mb-3" />
                  <p className="text-sm font-medium text-neutral-600">No failed tasks</p>
                  <p className="text-xs text-neutral-400 mt-1">All tasks are running smoothly</p>
                </td>
              </tr>
            ) : (
              filtered.map((task: any) => (
                <tr key={task.id} className="border-b border-neutral-100 hover:bg-neutral-50 dark:bg-neutral-800/50">
                  <td className="px-4 py-3 text-xs font-medium text-neutral-900 max-w-[200px] truncate">
                    {task.task_title}
                  </td>
                  <td className="px-4 py-3 text-xs text-neutral-600">{task.agent_name}</td>
                  <td className="px-4 py-3">
                    <div className="max-w-[250px]">
                      <span className="badge-red text-[10px] mb-1 inline-block">{task.error_type}</span>
                      <p className="text-xs text-neutral-500 truncate">{task.error_message}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-neutral-500 whitespace-nowrap">
                    {formatDate(task.failed_at)}
                  </td>
                  <td className="px-4 py-3 text-xs text-neutral-600 text-center">
                    {task.retry_count}/{task.max_retries}
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn(
                      task.status === "pending_retry" ? "badge-yellow" : "badge-red"
                    )}>
                      {task.status === "pending_retry" ? "Pending Retry" : "Permanently Failed"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setSelectedTask(task)}
                        className="p-1.5 rounded hover:bg-neutral-100 text-neutral-400 hover:text-neutral-600"
                        title="View Details"
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </button>
                      {task.status === "pending_retry" && (
                        <button
                          onClick={() => retryMutation.mutate(task.id)}
                          className="p-1.5 rounded hover:bg-neutral-100 text-neutral-400 hover:text-blue-600"
                          title="Retry"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                        </button>
                      )}
                      <button
                        onClick={() => discardMutation.mutate(task.id)}
                        className="p-1.5 rounded hover:bg-neutral-100 text-neutral-400 hover:text-red-600"
                        title="Discard"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Detail Modal */}
      {selectedTask && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setSelectedTask(null)}>
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-5 border-b border-neutral-100">
              <div>
                <h2 className="text-sm font-bold text-neutral-900 dark:text-white">{selectedTask.task_title}</h2>
                <p className="text-xs text-neutral-400 mt-0.5">Agent: {selectedTask.agent_name}</p>
              </div>
              <button onClick={() => setSelectedTask(null)} className="p-1 rounded hover:bg-neutral-100">
                <X className="h-4 w-4 text-neutral-400 dark:text-neutral-500" />
              </button>
            </div>

            <div className="p-5 space-y-5">
              {/* Error Info */}
              <div>
                <h3 className="text-xs font-semibold text-neutral-700 mb-2">Error Details</h3>
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <span className="badge-red text-[10px]">{selectedTask.error_type}</span>
                  <p className="text-xs text-red-700 mt-2">{selectedTask.error_message}</p>
                </div>
              </div>

              {/* Stack Trace */}
              <div>
                <h3 className="text-xs font-semibold text-neutral-700 mb-2">Stack Trace</h3>
                <pre className="bg-neutral-900 text-green-400 rounded-lg p-4 text-[11px] leading-relaxed overflow-x-auto font-mono">
                  {selectedTask.stack_trace}
                </pre>
              </div>

              {/* Metadata */}
              <div>
                <h3 className="text-xs font-semibold text-neutral-700 mb-2">Task Metadata</h3>
                <div className="bg-neutral-50 rounded-lg p-3 grid grid-cols-2 gap-2">
                  {Object.entries(selectedTask.metadata ?? {}).map(([key, value]) => (
                    <div key={key}>
                      <span className="text-[10px] text-neutral-400 uppercase">{key.replace(/_/g, " ")}</span>
                      <p className="text-xs text-neutral-700 font-medium">{String(value)}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Execution History */}
              <div>
                <h3 className="text-xs font-semibold text-neutral-700 mb-2">Execution History</h3>
                {(selectedTask.execution_history ?? []).length === 0 ? (
                  <p className="text-xs text-neutral-400 dark:text-neutral-500">No execution attempts yet</p>
                ) : (
                  <div className="space-y-2">
                    {selectedTask.execution_history.map((h: any, i: number) => (
                      <div key={i} className="flex items-center gap-3 bg-neutral-50 rounded-lg p-3 text-xs">
                        <span className="font-bold text-neutral-400 dark:text-neutral-500">#{h.attempt}</span>
                        <div className="flex-1">
                          <p className="text-neutral-600">
                            Started: {formatDate(h.started_at)}
                          </p>
                          <p className="text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">
                            Failed: {formatDate(h.failed_at)}
                          </p>
                        </div>
                        <span className="badge-red text-[10px]">{h.error}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 p-5 border-t border-neutral-100">
              {selectedTask.status === "pending_retry" && (
                <button
                  onClick={() => { retryMutation.mutate(selectedTask.id); setSelectedTask(null); }}
                  className="btn-primary text-sm flex items-center gap-1.5"
                >
                  <RefreshCw className="h-3.5 w-3.5" /> Retry Task
                </button>
              )}
              <button
                onClick={() => { discardMutation.mutate(selectedTask.id); setSelectedTask(null); }}
                className="btn-danger text-sm flex items-center gap-1.5"
              >
                <Trash2 className="h-3.5 w-3.5" /> Discard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
