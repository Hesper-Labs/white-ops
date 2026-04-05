import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  XCircle,
  ClipboardList,
  User,
  Calendar,
  Clock,
  AlertTriangle,
  FileText,
  Download,
  Terminal,
  MessageSquare,
  Send,
  Bot,
  RefreshCw,
  Flag,
  Target,
  CheckCircle2,
} from "lucide-react";
import { tasksApi } from "../api/endpoints";
import { formatDate } from "../lib/utils";
import toast from "react-hot-toast";

const statusColors: Record<string, string> = {
  pending: "badge-gray",
  assigned: "badge-blue",
  in_progress: "badge-yellow",
  review: "badge-blue",
  completed: "badge-green",
  failed: "badge-red",
  cancelled: "badge-gray",
};

const priorityConfig: Record<string, { badge: string; icon: string }> = {
  critical: { badge: "badge-red", icon: "text-red-500" },
  high: { badge: "badge-yellow", icon: "text-orange-500" },
  medium: { badge: "badge-blue", icon: "text-blue-500" },
  low: { badge: "badge-gray", icon: "text-neutral-400" },
};

const MOCK_TOOL_CALLS = [
  { ts: "2025-04-05T09:00:02Z", tool: "web_search", input: 'query="competitor pricing SaaS 2025"', output: "Found 12 results", status: "ok", duration: "1.4s" },
  { ts: "2025-04-05T09:00:04Z", tool: "browser", input: "navigate https://competitor-a.com/pricing", output: "Page loaded (200)", status: "ok", duration: "2.8s" },
  { ts: "2025-04-05T09:00:07Z", tool: "web_scraper", input: "extract .pricing-table", output: "3 pricing tiers extracted", status: "ok", duration: "1.1s" },
  { ts: "2025-04-05T09:00:09Z", tool: "browser", input: "navigate https://competitor-b.com/plans", output: "Page loaded (200)", status: "ok", duration: "3.2s" },
  { ts: "2025-04-05T09:00:13Z", tool: "web_scraper", input: "extract .plan-card", output: "4 plans extracted", status: "ok", duration: "0.9s" },
  { ts: "2025-04-05T09:00:14Z", tool: "data_analysis", input: "compare pricing across 5 competitors", output: "Analysis complete, 15 data points", status: "ok", duration: "4.2s" },
  { ts: "2025-04-05T09:00:19Z", tool: "excel", input: "create comparison_matrix.xlsx", output: "Spreadsheet created with 3 sheets", status: "ok", duration: "2.6s" },
  { ts: "2025-04-05T09:00:22Z", tool: "data_visualization", input: "bar chart: price_comparison", output: "Chart saved as price_chart.png", status: "ok", duration: "1.8s" },
  { ts: "2025-04-05T09:00:24Z", tool: "pdf", input: "generate pricing_report.pdf", output: "12-page report generated", status: "ok", duration: "5.1s" },
  { ts: "2025-04-05T09:00:30Z", tool: "internal_email", input: "notify requester: report ready", output: "Email sent", status: "ok", duration: "0.6s" },
];

const MOCK_OUTPUT_FILES = [
  { id: "of1", filename: "pricing_report.pdf", size: "2.4 MB", type: "application/pdf" },
  { id: "of2", filename: "comparison_matrix.xlsx", size: "145 KB", type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
  { id: "of3", filename: "price_chart.png", size: "89 KB", type: "image/png" },
];

const MOCK_COMMENTS = [
  { id: "cm1", author: "System Admin", text: "Please include annual pricing, not just monthly.", created_at: "2025-04-05T08:45:00Z" },
  { id: "cm2", author: "Research Agent", text: "Noted. I will collect both monthly and annual pricing tiers for each competitor.", created_at: "2025-04-05T08:50:00Z" },
  { id: "cm3", author: "System Admin", text: "Also add a notes column for any special enterprise deals mentioned.", created_at: "2025-04-05T09:05:00Z" },
];

const MOCK_AGENT_NAMES: Record<string, string> = {
  "a1b2c3d4-1111-4444-8888-000000000001": "Research Agent",
  "a1b2c3d4-1111-4444-8888-000000000002": "Data Analyst",
  "a1b2c3d4-1111-4444-8888-000000000003": "Office Assistant",
  "a1b2c3d4-1111-4444-8888-000000000004": "Developer Bot",
  "a1b2c3d4-1111-4444-8888-000000000005": "HR Coordinator",
};

export default function TaskDetail() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["task", taskId],
    queryFn: () => tasksApi.get(taskId!),
    enabled: !!taskId,
  });

  const cancelMut = useMutation({
    mutationFn: (id: string) => tasksApi.cancel(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["task", taskId] }); toast.success("Task cancelled"); },
  });

  const task: any = data?.data ?? null;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin" />
      </div>
    );
  }

  if (!task) {
    return (
      <div className="card p-12 text-center">
        <ClipboardList className="h-10 w-10 text-neutral-300 mx-auto mb-3" />
        <p className="text-sm font-medium text-neutral-600">Task not found</p>
        <button className="btn-secondary mt-4" onClick={() => navigate("/tasks")}>Back to Tasks</button>
      </div>
    );
  }

  const status = task.status as string;
  const priority = task.priority as string;
  const statusBadge = statusColors[status] ?? "badge-gray";
  const prioConfig = priorityConfig[priority] ?? { badge: "badge-gray", icon: "text-neutral-400" };
  const canCancel = !["completed", "cancelled", "failed"].includes(status);
  const agentName = task.agent_id ? (MOCK_AGENT_NAMES[task.agent_id as string] ?? task.agent_id) : "Unassigned";

  return (
    <div>
      {/* Back nav */}
      <button onClick={() => navigate("/tasks")} className="btn-ghost flex items-center gap-1.5 mb-4 text-neutral-500 hover:text-neutral-900">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to Tasks
      </button>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <h1 className="text-lg font-bold text-neutral-900">{task.title}</h1>
            <span className={statusBadge}>{status.replace("_", " ")}</span>
            <span className={prioConfig.badge}>{priority}</span>
          </div>
          {task.description && (
            <p className="text-xs text-neutral-400 mt-0.5 max-w-2xl">{task.description}</p>
          )}
        </div>
        {canCancel && (
          <button
            className="btn-secondary flex items-center gap-1.5 text-red-500 hover:text-red-700"
            onClick={() => cancelMut.mutate(task.id)}
            disabled={cancelMut.isPending}
          >
            <XCircle className="h-3.5 w-3.5" /> {cancelMut.isPending ? "Cancelling..." : "Cancel Task"}
          </button>
        )}
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left column - Info + Result */}
        <div className="col-span-2 space-y-6">
          {/* Task Information */}
          <div className="card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-neutral-900">Task Information</h3>
            <div className="grid grid-cols-2 gap-y-3 gap-x-6">
              <InfoRow icon={<Bot className="h-3.5 w-3.5" />} label="Agent" value={agentName} />
              <InfoRow icon={<User className="h-3.5 w-3.5" />} label="Created By" value={task.assigned_by ?? "System"} />
              <InfoRow icon={<Calendar className="h-3.5 w-3.5" />} label="Created" value={formatDate(task.created_at)} />
              <InfoRow icon={<Clock className="h-3.5 w-3.5" />} label="Started" value={task.started_at ? formatDate(task.started_at) : "Not started"} />
              <InfoRow icon={<CheckCircle2 className="h-3.5 w-3.5" />} label="Completed" value={task.completed_at ? formatDate(task.completed_at) : "In progress"} />
              <InfoRow icon={<Target className="h-3.5 w-3.5" />} label="Deadline" value={task.deadline ? formatDate(task.deadline) : "No deadline"} />
              <InfoRow icon={<RefreshCw className="h-3.5 w-3.5" />} label="Retries" value={`${task.retry_count ?? 0} / ${task.max_retries ?? 3}`} />
              <InfoRow icon={<Flag className="h-3.5 w-3.5" />} label="Priority" value={priority} />
            </div>
            {task.instructions && (
              <div className="pt-2">
                <h4 className="text-xs font-medium text-neutral-500 mb-1">Instructions</h4>
                <p className="text-sm text-neutral-600 bg-neutral-50 rounded p-3 leading-relaxed">{task.instructions}</p>
              </div>
            )}
          </div>

          {/* Result / Error */}
          {status === "completed" && task.result && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Result
              </h3>
              <pre className="bg-neutral-50 border border-neutral-200 rounded-lg p-4 text-sm text-neutral-700 font-mono whitespace-pre-wrap overflow-x-auto">
                {task.result}
              </pre>
            </div>
          )}

          {status === "failed" && task.error && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-red-600 mb-3 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-red-500" /> Error
              </h3>
              <pre className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700 font-mono whitespace-pre-wrap overflow-x-auto">
                {task.error}
              </pre>
            </div>
          )}

          {/* Output Files */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
              <FileText className="h-4 w-4 text-neutral-500" /> Output Files
            </h3>
            {MOCK_OUTPUT_FILES.length === 0 ? (
              <p className="text-xs text-neutral-400">No output files generated.</p>
            ) : (
              <div className="space-y-2">
                {MOCK_OUTPUT_FILES.map((file) => (
                  <div key={file.id} className="flex items-center justify-between py-2 px-3 bg-neutral-50 rounded-lg">
                    <div className="flex items-center gap-2.5">
                      <FileText className="h-4 w-4 text-neutral-400" />
                      <div>
                        <p className="text-sm font-medium text-neutral-700">{file.filename}</p>
                        <p className="text-[10px] text-neutral-400">{file.size}</p>
                      </div>
                    </div>
                    <button className="btn-ghost flex items-center gap-1 text-xs" onClick={() => toast.success(`Download ${file.filename} (demo)`)}>
                      <Download className="h-3 w-3" /> Download
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Tool Calls Log */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
              <Terminal className="h-4 w-4 text-neutral-500" /> Tool Calls
            </h3>
            <div className="bg-neutral-900 rounded-lg p-4 font-mono text-xs leading-relaxed overflow-x-auto">
              {MOCK_TOOL_CALLS.map((call, i) => {
                const time = new Date(call.ts).toLocaleTimeString("en-US", { hour12: false });
                const color = call.status === "ok" ? "text-emerald-400" : "text-red-400";
                return (
                  <div key={i} className="flex gap-3 hover:bg-neutral-800 px-2 py-0.5 rounded">
                    <span className="text-neutral-500 shrink-0">{time}</span>
                    <span className={`${color} shrink-0`}>[{call.status.toUpperCase().padEnd(5)}]</span>
                    <span className="text-cyan-400 shrink-0 w-28">{call.tool}</span>
                    <span className="text-neutral-300 truncate">{call.input}</span>
                    <span className="text-neutral-500 ml-auto shrink-0">{call.duration}</span>
                  </div>
                );
              })}
              <div className="flex gap-3 px-2 py-0.5 mt-2 text-neutral-500">
                <span>---</span>
                <span>Task execution complete ({MOCK_TOOL_CALLS.length} tool calls)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right column - Comments */}
        <div className="space-y-6">
          <CommentsSection />
        </div>
      </div>
    </div>
  );
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="text-neutral-400">{icon}</span>
      <span className="text-xs text-neutral-400 w-20">{label}</span>
      <span className="text-sm text-neutral-700 font-medium">{value}</span>
    </div>
  );
}

function CommentsSection() {
  const [comments, setComments] = useState(MOCK_COMMENTS);
  const [newComment, setNewComment] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    setComments((prev) => [
      ...prev,
      {
        id: `cm-${Date.now()}`,
        author: "System Admin",
        text: newComment.trim(),
        created_at: new Date().toISOString(),
      },
    ]);
    setNewComment("");
    toast.success("Comment added");
  };

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-neutral-900 mb-4 flex items-center gap-2">
        <MessageSquare className="h-4 w-4 text-neutral-500" /> Comments
        <span className="badge-gray ml-1">{comments.length}</span>
      </h3>

      {/* Comment list */}
      <div className="space-y-4 mb-4 max-h-96 overflow-y-auto">
        {comments.map((comment) => (
          <div key={comment.id} className="border-b border-neutral-100 pb-3 last:border-0">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-5 h-5 rounded-full bg-neutral-200 flex items-center justify-center">
                <User className="h-3 w-3 text-neutral-500" />
              </div>
              <span className="text-xs font-semibold text-neutral-700">{comment.author}</span>
              <span className="text-[10px] text-neutral-300">{formatDate(comment.created_at)}</span>
            </div>
            <p className="text-xs text-neutral-600 leading-relaxed pl-7">{comment.text}</p>
          </div>
        ))}
      </div>

      {/* Add comment form */}
      <form onSubmit={handleSubmit} className="space-y-2">
        <textarea
          className="input text-xs"
          rows={3}
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Add a comment..."
        />
        <button type="submit" className="btn-primary w-full flex items-center justify-center gap-1.5 text-xs" disabled={!newComment.trim()}>
          <Send className="h-3 w-3" /> Add Comment
        </button>
      </form>
    </div>
  );
}
