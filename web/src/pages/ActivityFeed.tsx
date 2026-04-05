import { Bot, CheckCircle2, AlertTriangle, Server, MessageSquare, FileText, Settings, LogIn, Zap } from "lucide-react";
import { formatDate } from "../lib/utils";

const DEMO_ACTIVITIES = [
  { id: "1", icon: "task_complete", text: "Research Agent completed 'Research competitor pricing'", time: "2025-04-05T11:30:00Z", type: "success" },
  { id: "2", icon: "message", text: "Data Analyst sent email to Office Assistant: 'Q1 charts for presentation'", time: "2025-04-05T11:00:00Z", type: "info" },
  { id: "3", icon: "task_start", text: "Office Assistant started 'Prepare board meeting presentation'", time: "2025-04-05T10:45:00Z", type: "info" },
  { id: "4", icon: "file", text: "Research Agent uploaded competitor-prices.csv (33.8 KB)", time: "2025-04-05T10:25:00Z", type: "info" },
  { id: "5", icon: "task_fail", text: "Developer Bot failed 'Fix API integration bug' - TimeoutError", time: "2025-04-05T07:30:00Z", type: "error" },
  { id: "6", icon: "worker", text: "Worker remote-worker-01 connected, awaiting approval", time: "2025-04-05T07:00:00Z", type: "warning" },
  { id: "7", icon: "task_complete", text: "Office Assistant completed 'Send weekly newsletter' - 247 recipients", time: "2025-04-04T14:30:00Z", type: "success" },
  { id: "8", icon: "task_complete", text: "Research Agent completed 'Translate product brochure to Turkish'", time: "2025-04-04T09:45:00Z", type: "success" },
  { id: "9", icon: "login", text: "System Admin logged in from 192.168.1.10", time: "2025-04-04T09:00:00Z", type: "info" },
  { id: "10", icon: "settings", text: "System Admin updated LLM default provider to Anthropic", time: "2025-04-04T08:30:00Z", type: "info" },
  { id: "11", icon: "agent", text: "HR Coordinator stopped by System Admin", time: "2025-04-03T17:00:00Z", type: "warning" },
  { id: "12", icon: "task_complete", text: "Data Analyst completed 'Generate Q1 Sales Report' - 24 pages", time: "2025-03-28T10:15:00Z", type: "success" },
];

const iconMap: Record<string, React.ElementType> = {
  task_complete: CheckCircle2, task_fail: AlertTriangle, task_start: Zap,
  message: MessageSquare, file: FileText, worker: Server,
  login: LogIn, settings: Settings, agent: Bot,
};

const typeColors: Record<string, string> = {
  success: "text-emerald-600 bg-emerald-50",
  error: "text-red-600 bg-red-50",
  warning: "text-amber-600 bg-amber-50",
  info: "text-blue-600 bg-blue-50",
};

export default function ActivityFeed() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-lg font-bold text-neutral-900">Activity Feed</h1>
        <p className="text-xs text-neutral-400 mt-0.5">Recent platform events</p>
      </div>

      <div className="card">
        <div className="divide-y divide-neutral-100">
          {DEMO_ACTIVITIES.map((activity) => {
            const Icon = iconMap[activity.icon] ?? Zap;
            const color = typeColors[activity.type] ?? typeColors.info;
            return (
              <div key={activity.id} className="flex items-start gap-3 px-5 py-3.5 hover:bg-neutral-50 transition-colors">
                <div className={`w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5 ${color}`}>
                  <Icon className="h-3.5 w-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-neutral-700">{activity.text}</p>
                </div>
                <span className="text-[11px] text-neutral-400 whitespace-nowrap flex-shrink-0">{formatDate(activity.time)}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
