import { useState, useEffect, useRef } from "react";
import {
  Bell, CheckCircle2, XCircle, Server, AlertTriangle,
  Bot, MessageSquare, Clock, X,
} from "lucide-react";
import { cn } from "../../lib/utils";

interface Notification {
  id: string;
  icon: "success" | "error" | "warning" | "info" | "agent" | "worker";
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

const ICON_MAP = {
  success: { icon: CheckCircle2, className: "text-emerald-500" },
  error: { icon: XCircle, className: "text-red-500" },
  warning: { icon: AlertTriangle, className: "text-amber-500" },
  info: { icon: MessageSquare, className: "text-blue-500" },
  agent: { icon: Bot, className: "text-violet-500" },
  worker: { icon: Server, className: "text-neutral-500" },
};

const INITIAL_NOTIFICATIONS: Notification[] = [
  { id: "n1", icon: "success", title: "Task Completed", message: "Q1 Revenue Analysis finished successfully", timestamp: "2 min ago", read: false },
  { id: "n2", icon: "error", title: "Task Failed", message: "Competitor Report Draft encountered an error", timestamp: "8 min ago", read: false },
  { id: "n3", icon: "worker", title: "Worker Connected", message: "worker-gpu-03 is now online", timestamp: "15 min ago", read: false },
  { id: "n4", icon: "agent", title: "Agent Error", message: "Financial Analyst exceeded token limit", timestamp: "22 min ago", read: false },
  { id: "n5", icon: "success", title: "Task Completed", message: "Weekly Newsletter generated and saved", timestamp: "1 hr ago", read: true },
  { id: "n6", icon: "warning", title: "Rate Limit Warning", message: "GPT-4o approaching 80% of daily quota", timestamp: "1 hr ago", read: true },
  { id: "n7", icon: "info", title: "New Message", message: "Research Specialist shared analysis results", timestamp: "2 hr ago", read: true },
  { id: "n8", icon: "worker", title: "Worker Disconnected", message: "worker-cpu-01 went offline unexpectedly", timestamp: "3 hr ago", read: true },
  { id: "n9", icon: "success", title: "Workflow Complete", message: "Daily report pipeline finished all steps", timestamp: "4 hr ago", read: true },
  { id: "n10", icon: "agent", title: "Agent Started", message: "Content Writer resumed after pause", timestamp: "5 hr ago", read: true },
];

export default function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>(INITIAL_NOTIFICATIONS);
  const panelRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const unreadCount = notifications.filter((n) => !n.read).length;

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  function markAllRead() {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }

  function markRead(id: string) {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
    );
  }

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        onClick={() => setOpen((prev) => !prev)}
        className="relative p-2 rounded-md text-neutral-500 hover:text-neutral-700 hover:bg-neutral-100 transition-colors"
        title="Notifications"
      >
        <Bell className="h-4.5 w-4.5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center h-4 min-w-[16px] px-1 rounded-full bg-red-500 text-white text-[9px] font-bold leading-none">
            {unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          ref={panelRef}
          className="absolute right-0 top-full mt-1 w-96 bg-white rounded-lg border border-neutral-200 shadow-lg z-50 overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
            <h3 className="text-sm font-semibold text-neutral-900">Notifications</h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={markAllRead}
                  className="text-[11px] font-medium text-neutral-500 hover:text-neutral-700 transition-colors"
                >
                  Mark all as read
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                className="p-0.5 rounded hover:bg-neutral-100 text-neutral-400 hover:text-neutral-600"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Notification list */}
          <div className="max-h-96 overflow-y-auto divide-y divide-neutral-100">
            {notifications.map((n) => {
              const meta = ICON_MAP[n.icon];
              const Icon = meta.icon;
              return (
                <button
                  key={n.id}
                  onClick={() => markRead(n.id)}
                  className={cn(
                    "w-full flex items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-neutral-50",
                    !n.read && "bg-blue-50/40",
                  )}
                >
                  <Icon className={cn("h-4 w-4 mt-0.5 flex-shrink-0", meta.className)} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className={cn("text-xs font-semibold truncate", n.read ? "text-neutral-600" : "text-neutral-900")}>
                        {n.title}
                      </p>
                      {!n.read && <span className="h-1.5 w-1.5 rounded-full bg-blue-500 flex-shrink-0" />}
                    </div>
                    <p className="text-xs text-neutral-500 mt-0.5 truncate">{n.message}</p>
                    <div className="flex items-center gap-1 mt-1">
                      <Clock className="h-3 w-3 text-neutral-300" />
                      <span className="text-[10px] text-neutral-400">{n.timestamp}</span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Footer */}
          <div className="px-4 py-2.5 border-t border-neutral-200 bg-neutral-50">
            <button
              onClick={() => setOpen(false)}
              className="w-full text-center text-[11px] font-medium text-neutral-500 hover:text-neutral-700 transition-colors"
            >
              View all notifications
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
