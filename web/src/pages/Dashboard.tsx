import { useQuery } from "@tanstack/react-query";
import { Bot, ListTodo, Server, MessageSquare, Activity } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { dashboardApi, analyticsApi } from "../api/endpoints";

function StatCard({ title, value, subtitle, icon: Icon }: { title: string; value: number | string; subtitle: string; icon: React.ElementType }) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">{title}</span>
        <Icon className="h-4 w-4 text-neutral-400 dark:text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />
      </div>
      <p className="text-2xl font-bold text-neutral-900 dark:text-white">{value}</p>
      <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">{subtitle}</p>
    </div>
  );
}

const PIE_COLORS = ["#10b981", "#3b82f6", "#6366f1", "#94a3b8", "#ef4444"];

const DEMO_WEEKLY = [
  { day: "Mon", completed: 8, failed: 1 },
  { day: "Tue", completed: 12, failed: 2 },
  { day: "Wed", completed: 6, failed: 0 },
  { day: "Thu", completed: 15, failed: 1 },
  { day: "Fri", completed: 10, failed: 3 },
  { day: "Sat", completed: 3, failed: 0 },
  { day: "Sun", completed: 1, failed: 0 },
];

export default function Dashboard() {
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: () => dashboardApi.overview(), refetchInterval: 10000 });
  const { data: analyticsData } = useQuery({ queryKey: ["analytics-overview-dash"], queryFn: () => analyticsApi.overview(7) });

  const overview = data?.data;
  const analytics = analyticsData?.data;

  if (isLoading) return <div className="flex items-center justify-center h-64"><div className="w-6 h-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin" /></div>;

  const pieData = overview?.tasks?.by_status
    ? Object.entries(overview.tasks.by_status as Record<string, number>).map(([name, value]) => ({ name: name.replace("_", " "), value: value as number }))
    : [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-neutral-900 dark:text-white">Dashboard</h1>
          <p className="text-xs text-neutral-400 mt-0.5">Platform overview</p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-emerald-600">
          <Activity className="h-3.5 w-3.5" />
          <span className="font-medium">All systems operational</span>
        </div>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <StatCard title="Agents" value={overview?.agents?.active ?? 0} subtitle={`${overview?.agents?.total ?? 0} total`} icon={Bot} />
        <StatCard title="Tasks" value={overview?.tasks?.total ?? 0} subtitle={`${overview?.tasks?.by_status?.in_progress ?? 0} running`} icon={ListTodo} />
        <StatCard title="Workers" value={overview?.workers?.online ?? 0} subtitle={`${overview?.workers?.total ?? 0} nodes`} icon={Server} />
        <StatCard title="Messages" value={overview?.messages?.total ?? 0} subtitle={`${overview?.messages?.unread ?? 0} unread`} icon={MessageSquare} />
      </div>

      {analytics && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="card p-5">
            <span className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Success Rate</span>
            <p className="text-2xl font-bold text-neutral-900 mt-2">{analytics.tasks.success_rate}%</p>
            <p className="text-xs text-neutral-500 mt-1">{analytics.tasks.completed}/{analytics.tasks.total} completed</p>
          </div>
          <div className="card p-5">
            <span className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Avg Completion</span>
            <p className="text-2xl font-bold text-neutral-900 mt-2">
              {analytics.tasks.avg_completion_seconds > 3600 ? `${Math.round(analytics.tasks.avg_completion_seconds / 3600)}h` : `${Math.round(analytics.tasks.avg_completion_seconds / 60)}m`}
            </p>
            <p className="text-xs text-neutral-500 mt-1">per task</p>
          </div>
          <div className="card p-5">
            <span className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Files Created</span>
            <p className="text-2xl font-bold text-neutral-900 mt-2">{analytics.files.total}</p>
            <p className="text-xs text-neutral-500 mt-1">{(analytics.files.total_size_bytes / 1024 / 1024).toFixed(1)} MB</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Weekly Task Chart */}
        <div className="card lg:col-span-2">
          <div className="px-5 py-3 border-b border-neutral-200 dark:border-neutral-700">
            <h2 className="text-sm font-semibold text-neutral-900 dark:text-white">Weekly Task Activity</h2>
          </div>
          <div className="p-5">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={DEMO_WEEKLY} barGap={2}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#999" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#999" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e5e5" }} />
                <Bar dataKey="completed" fill="#10b981" radius={[3, 3, 0, 0]} name="Completed" />
                <Bar dataKey="failed" fill="#ef4444" radius={[3, 3, 0, 0]} name="Failed" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Task Distribution Pie */}
        <div className="card">
          <div className="px-5 py-3 border-b border-neutral-200 dark:border-neutral-700">
            <h2 className="text-sm font-semibold text-neutral-900 dark:text-white">Task Distribution</h2>
          </div>
          <div className="p-5 flex flex-col items-center">
            {pieData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={160}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={40} outerRadius={65} paddingAngle={3} dataKey="value">
                      {pieData.map((_entry, index) => (
                        <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8, border: "1px solid #e5e5e5" }} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-wrap gap-3 mt-2 justify-center">
                  {pieData.map((entry, i) => (
                    <div key={entry.name} className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                      <span className="text-[10px] text-neutral-500 capitalize">{entry.name}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-sm text-neutral-400 py-12">No data</p>
            )}
          </div>
        </div>
      </div>

      {/* System Health */}
      <div className="card">
        <div className="px-5 py-3 border-b border-neutral-200 dark:border-neutral-700">
          <h2 className="text-sm font-semibold text-neutral-900 dark:text-white">System Health</h2>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-6 divide-x divide-neutral-100">
          {["API Server", "PostgreSQL", "Redis", "MinIO Storage", "Mail Server", "WebSocket"].map((name) => (
            <div key={name} className="flex items-center gap-2.5 px-5 py-3.5">
              <div className="status-dot online" />
              <div>
                <span className="text-xs font-medium text-neutral-700 dark:text-neutral-300">{name}</span>
                <p className="text-[10px] text-emerald-600">Healthy</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
