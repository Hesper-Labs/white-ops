import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2, XCircle, Clock,
} from "lucide-react";
import api from "../api/client";
import { cn, formatDate } from "../lib/utils";
import toast from "react-hot-toast";

const DEMO_APPROVALS = [
  {
    id: "apr1", type: "dangerous_action", status: "pending",
    agent_name: "DevOps Agent", action: "Execute shell command: rm -rf /tmp/build/*",
    risk_level: "high", requested_at: "2026-04-08T11:45:00Z",
  },
  {
    id: "apr2", type: "external_api", status: "pending",
    agent_name: "Research Agent", action: "Send email via SMTP to client@example.com",
    risk_level: "medium", requested_at: "2026-04-08T11:30:00Z",
  },
  {
    id: "apr3", type: "file_write", status: "approved",
    agent_name: "Data Agent", action: "Write report to /shared/reports/q1-analysis.pdf",
    risk_level: "low", requested_at: "2026-04-08T10:00:00Z", resolved_at: "2026-04-08T10:05:00Z",
  },
  {
    id: "apr4", type: "dangerous_action", status: "rejected",
    agent_name: "Automation Agent", action: "Modify production database schema",
    risk_level: "critical", requested_at: "2026-04-07T16:00:00Z", resolved_at: "2026-04-07T16:02:00Z",
  },
];

const riskColors: Record<string, string> = {
  low: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  critical: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

const statusIcons: Record<string, React.ReactNode> = {
  pending: <Clock className="h-4 w-4 text-amber-500" />,
  approved: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
  rejected: <XCircle className="h-4 w-4 text-red-500" />,
};

export default function Approvals() {
  const [filter, setFilter] = useState<string>("all");
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["approvals"],
    queryFn: () => api.get("/approvals/").then((r) => r.data),
    placeholderData: DEMO_APPROVALS,
  });

  const approvals = data ?? DEMO_APPROVALS;
  const filtered = filter === "all" ? approvals : approvals.filter((a: Record<string, unknown>) => a.status === filter);

  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api.post(`/approvals/${id}/${action}`),
    onSuccess: (_, { action }) => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      toast.success(`Request ${action}d`);
    },
    onError: () => toast.error("Action failed"),
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold">Approval Requests</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
          Review and approve high-risk agent actions
        </p>
      </div>

      <div className="flex gap-2">
        {["all", "pending", "approved", "rejected"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors",
              filter === f
                ? "bg-neutral-900 text-white border-neutral-900 dark:bg-white dark:text-neutral-900 dark:border-white"
                : "bg-white text-neutral-600 border-neutral-200 hover:bg-neutral-50 dark:bg-neutral-800 dark:text-neutral-400 dark:border-neutral-700",
            )}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <div className="grid gap-3">
        {filtered.map((approval: Record<string, unknown>) => (
          <div
            key={approval.id as string}
            className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg p-4"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                {statusIcons[approval.status as string]}
                <div>
                  <p className="text-sm font-semibold">{approval.action as string}</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                    {approval.agent_name as string} &middot; {formatDate(approval.requested_at as string)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn("text-[11px] font-medium px-2 py-0.5 rounded-full", riskColors[approval.risk_level as string])}>
                  {approval.risk_level as string}
                </span>
                {approval.status === "pending" && (
                  <div className="flex gap-1">
                    <button
                      onClick={() => actionMutation.mutate({ id: approval.id as string, action: "approve" })}
                      className="px-2 py-1 text-xs font-medium bg-emerald-600 text-white rounded hover:bg-emerald-700"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => actionMutation.mutate({ id: approval.id as string, action: "reject" })}
                      className="px-2 py-1 text-xs font-medium bg-red-600 text-white rounded hover:bg-red-700"
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
