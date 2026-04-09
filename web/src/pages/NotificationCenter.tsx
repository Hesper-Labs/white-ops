import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2, AlertTriangle, Info, XCircle,
  Check,
} from "lucide-react";
import api from "../api/client";
import { cn, formatDate } from "../lib/utils";
import toast from "react-hot-toast";

const DEMO_NOTIFICATIONS = [
  {
    id: "n1", type: "success", title: "Task Completed",
    message: "Research Agent finished 'Market Analysis Q1' successfully.",
    read: false, created_at: "2026-04-08T11:45:00Z",
  },
  {
    id: "n2", type: "warning", title: "Budget Alert",
    message: "DevOps Agent has used 85% of its monthly budget ($42.50 / $50.00).",
    read: false, created_at: "2026-04-08T10:30:00Z",
  },
  {
    id: "n3", type: "error", title: "Task Failed",
    message: "Data Agent failed on 'CSV Import': connection timeout after 3 retries.",
    read: false, created_at: "2026-04-08T09:15:00Z",
  },
  {
    id: "n4", type: "info", title: "New Agent Online",
    message: "Code Review Agent is now active on worker-03.",
    read: true, created_at: "2026-04-07T16:00:00Z",
  },
  {
    id: "n5", type: "success", title: "Workflow Complete",
    message: "Daily Report Pipeline finished all 5 steps.",
    read: true, created_at: "2026-04-07T09:05:00Z",
  },
];

const typeConfig: Record<string, { icon: React.ReactNode; color: string }> = {
  success: { icon: <CheckCircle2 className="h-4 w-4" />, color: "text-emerald-500" },
  warning: { icon: <AlertTriangle className="h-4 w-4" />, color: "text-amber-500" },
  error: { icon: <XCircle className="h-4 w-4" />, color: "text-red-500" },
  info: { icon: <Info className="h-4 w-4" />, color: "text-blue-500" },
};

export default function NotificationCenter() {
  const [filter, setFilter] = useState<string>("all");
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.get("/notifications/").then((r) => r.data),
    placeholderData: DEMO_NOTIFICATIONS,
  });

  const notifications = data ?? DEMO_NOTIFICATIONS;
  const filtered = filter === "all"
    ? notifications
    : filter === "unread"
      ? notifications.filter((n: Record<string, unknown>) => !n.read)
      : notifications.filter((n: Record<string, unknown>) => n.type === filter);

  const markReadMutation = useMutation({
    mutationFn: (id: string) => api.patch(`/notifications/${id}`, { read: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: () => toast.error("Failed to update"),
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => api.post("/notifications/mark-all-read"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      toast.success("All marked as read");
    },
    onError: () => toast.error("Failed to update"),
  });

  const unreadCount = notifications.filter((n: Record<string, unknown>) => !n.read).length;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Notifications</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
            {unreadCount} unread notification{unreadCount !== 1 ? "s" : ""}
          </p>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={() => markAllReadMutation.mutate()}
            className="flex items-center gap-2 px-3 py-2 text-xs font-medium border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800"
          >
            <Check className="h-3.5 w-3.5" /> Mark all read
          </button>
        )}
      </div>

      <div className="flex gap-2">
        {["all", "unread", "error", "warning", "success", "info"].map((f) => (
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

      <div className="space-y-2">
        {filtered.map((notif: Record<string, unknown>) => {
          const config = (typeConfig as Record<string, any>)[notif.type as string] ?? typeConfig.info;
          return (
            <div
              key={notif.id as string}
              onClick={() => !notif.read && markReadMutation.mutate(notif.id as string)}
              className={cn(
                "bg-white dark:bg-neutral-800 border rounded-lg p-4 cursor-pointer transition-colors",
                notif.read
                  ? "border-neutral-200 dark:border-neutral-700 opacity-60"
                  : "border-neutral-300 dark:border-neutral-600",
              )}
            >
              <div className="flex items-start gap-3">
                <div className={cn("mt-0.5", config.color)}>{config.icon}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold">{notif.title as string}</p>
                    <span className="text-[11px] text-neutral-400 dark:text-neutral-500">{formatDate(notif.created_at as string)}</span>
                  </div>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">{notif.message as string}</p>
                </div>
                {!notif.read && <div className="h-2 w-2 rounded-full bg-blue-500 mt-1.5 shrink-0" />}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
