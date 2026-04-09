import { useQuery } from "@tanstack/react-query";
import { Filter } from "lucide-react";
import { adminApi } from "../api/endpoints";
import { formatDate } from "../lib/utils";
import { useState } from "react";

const DEMO_LOGS = [
  { id: "al1", action: "login_success", resource_type: "auth", actor_type: "user", actor_id: "u1", details: "User admin@whiteops.local logged in", created_at: "2025-04-05T11:30:00Z" },
  { id: "al2", action: "agent_created", resource_type: "agent", resource_id: "a1", actor_type: "user", actor_id: "u1", details: "Created agent: Research Agent", created_at: "2025-04-05T11:25:00Z" },
  { id: "al3", action: "task_assigned", resource_type: "task", resource_id: "t2", actor_type: "system", actor_id: null, details: "Task 'Research competitor pricing' assigned to Research Agent", created_at: "2025-04-05T10:00:00Z" },
  { id: "al4", action: "task_completed", resource_type: "task", resource_id: "t1", actor_type: "agent", actor_id: "a2", details: "Task 'Generate Q1 Sales Report' completed successfully", created_at: "2025-04-05T09:15:00Z" },
  { id: "al5", action: "worker_approved", resource_type: "worker", resource_id: "w2", actor_type: "user", actor_id: "u1", details: "Worker office-server-02 approved", created_at: "2025-04-04T14:00:00Z" },
  { id: "al6", action: "task_failed", resource_type: "task", resource_id: "t5", actor_type: "agent", actor_id: "a4", details: "Task 'Fix API integration bug' failed: TimeoutError", created_at: "2025-04-05T07:30:00Z" },
  { id: "al7", action: "settings_updated", resource_type: "settings", actor_type: "user", actor_id: "u1", details: "Updated llm.default_provider to anthropic", created_at: "2025-04-04T10:00:00Z" },
  { id: "al8", action: "file_uploaded", resource_type: "file", resource_id: "f1", actor_type: "agent", actor_id: "a2", details: "Uploaded q1-sales-report.pdf (2.3 MB)", created_at: "2025-03-28T10:15:00Z" },
  { id: "al9", action: "login_failed", resource_type: "auth", actor_type: "user", actor_id: null, details: "Failed login attempt for unknown@test.com", created_at: "2025-04-05T06:00:00Z" },
  { id: "al10", action: "agent_stopped", resource_type: "agent", resource_id: "a5", actor_type: "user", actor_id: "u1", details: "Agent HR Coordinator stopped", created_at: "2025-04-04T17:00:00Z" },
];

const actionColors: Record<string, string> = {
  login_success: "badge-green",
  login_failed: "badge-red",
  agent_created: "badge-blue",
  agent_stopped: "badge-gray",
  task_assigned: "badge-blue",
  task_completed: "badge-green",
  task_failed: "badge-red",
  worker_approved: "badge-green",
  settings_updated: "badge-yellow",
  file_uploaded: "badge-purple",
};

export default function AuditLog() {
  const [filter, setFilter] = useState("");

  const { data } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => adminApi.auditLogs(),
  });

  const logs = (data?.data?.length ? data.data : DEMO_LOGS) as any[];
  const filtered = filter ? logs.filter((l: any) => l.action.includes(filter) || l.resource_type.includes(filter)) : logs;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-neutral-900 dark:text-white">Audit Log</h1>
          <p className="text-xs text-neutral-400 mt-0.5">{logs.length} events recorded</p>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-neutral-400 dark:text-neutral-500" />
          <input className="input w-64" placeholder="Filter by action or resource..." value={filter} onChange={(e) => setFilter(e.target.value)} />
        </div>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr>
              <th className="table-header">Time</th>
              <th className="table-header">Action</th>
              <th className="table-header">Resource</th>
              <th className="table-header">Actor</th>
              <th className="table-header">Details</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((log: any) => (
              <tr key={log.id} className="border-b border-neutral-100 hover:bg-neutral-50 dark:bg-neutral-800/50">
                <td className="px-4 py-3 text-xs text-neutral-500 whitespace-nowrap">{formatDate(log.created_at)}</td>
                <td className="px-4 py-3"><span className={actionColors[log.action] ?? "badge-gray"}>{log.action}</span></td>
                <td className="px-4 py-3 text-xs text-neutral-600">{log.resource_type}</td>
                <td className="px-4 py-3 text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{log.actor_type}{log.actor_id ? ` (${String(log.actor_id).slice(0, 6)})` : ""}</td>
                <td className="px-4 py-3 text-xs text-neutral-600 max-w-md truncate">{log.details}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
