import { useState } from "react";
import { Plus, Play, Pause, Trash2 } from "lucide-react";
import toast from "react-hot-toast";

const DEMO_SCHEDULES = [
  { id: "s1", name: "Weekly Sales Report", cron: "0 9 * * 1", description: "Generate Q1 sales report and email to management", agent: "Data Analyst", enabled: true, last_run: "2025-03-31T09:00:00Z", next_run: "2025-04-07T09:00:00Z" },
  { id: "s2", name: "Daily Competitor Check", cron: "0 8 * * 1-5", description: "Scrape competitor pricing and update spreadsheet", agent: "Research Agent", enabled: true, last_run: "2025-04-04T08:00:00Z", next_run: "2025-04-07T08:00:00Z" },
  { id: "s3", name: "Monthly Invoice Generation", cron: "0 10 1 * *", description: "Generate invoices for all active clients", agent: "Office Assistant", enabled: true, last_run: "2025-04-01T10:00:00Z", next_run: "2025-05-01T10:00:00Z" },
  { id: "s4", name: "Backup Database", cron: "0 2 * * *", description: "Create database backup and upload to cloud storage", agent: "Developer Bot", enabled: false, last_run: "2025-04-04T02:00:00Z", next_run: null },
];

export default function ScheduledTasks() {
  const [showCreate, setShowCreate] = useState(false);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-neutral-900 dark:text-white">Scheduled Tasks</h1>
          <p className="text-xs text-neutral-400 mt-0.5">Recurring automated tasks</p>
        </div>
        <button className="btn-primary flex items-center gap-1.5" onClick={() => setShowCreate(true)}>
          <Plus className="h-3.5 w-3.5" /> New Schedule
        </button>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr>
              <th className="table-header">Task</th>
              <th className="table-header">Schedule</th>
              <th className="table-header">Agent</th>
              <th className="table-header">Status</th>
              <th className="table-header">Last Run</th>
              <th className="table-header">Next Run</th>
              <th className="table-header w-24">Actions</th>
            </tr>
          </thead>
          <tbody>
            {DEMO_SCHEDULES.map((s) => (
              <tr key={s.id} className="border-b border-neutral-100 hover:bg-neutral-50 dark:bg-neutral-800/50">
                <td className="px-4 py-3">
                  <p className="text-sm font-semibold text-neutral-900 dark:text-white">{s.name}</p>
                  <p className="text-xs text-neutral-400 mt-0.5">{s.description}</p>
                </td>
                <td className="px-4 py-3"><code className="text-xs bg-neutral-100 px-2 py-1 rounded font-mono">{s.cron}</code></td>
                <td className="px-4 py-3 text-sm text-neutral-600">{s.agent}</td>
                <td className="px-4 py-3">{s.enabled ? <span className="badge-green">active</span> : <span className="badge-gray">paused</span>}</td>
                <td className="px-4 py-3 text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{s.last_run ? new Date(s.last_run).toLocaleDateString() : "-"}</td>
                <td className="px-4 py-3 text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{s.next_run ? new Date(s.next_run).toLocaleDateString() : "-"}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1 justify-end">
                    <button className="btn-ghost" title={s.enabled ? "Pause" : "Resume"} onClick={() => toast.success(s.enabled ? "Paused" : "Resumed")}>
                      {s.enabled ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                    </button>
                    <button className="btn-ghost text-red-400 hover:text-red-600" title="Delete"><Trash2 className="h-3.5 w-3.5" /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="card p-6 w-full max-w-md shadow-lg" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-sm font-bold text-neutral-900 mb-4">New Scheduled Task</h2>
            <form onSubmit={(e) => { e.preventDefault(); toast.success("Schedule created (demo)"); setShowCreate(false); }} className="space-y-3">
              <div><label className="block text-xs font-medium text-neutral-500 mb-1">Name</label><input className="input" required placeholder="Weekly Report" /></div>
              <div><label className="block text-xs font-medium text-neutral-500 mb-1">Description</label><input className="input" placeholder="What should be done" /></div>
              <div><label className="block text-xs font-medium text-neutral-500 mb-1">Cron Expression</label><input className="input font-mono" required placeholder="0 9 * * 1" /></div>
              <div><label className="block text-xs font-medium text-neutral-500 mb-1">Assign to Agent</label>
                <select className="input"><option>Research Agent</option><option>Data Analyst</option><option>Office Assistant</option><option>Developer Bot</option></select>
              </div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" className="btn-primary flex-1">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
