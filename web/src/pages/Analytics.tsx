import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  TrendingUp,
  Clock,
  Target,
  Cpu,
} from "lucide-react";
import { analyticsApi } from "../api/endpoints";

export default function Analytics() {
  const [period, setPeriod] = useState(7);

  const { data: overviewData } = useQuery({
    queryKey: ["analytics-overview", period],
    queryFn: () => analyticsApi.overview(period),
  });

  const { data: agentData } = useQuery({
    queryKey: ["analytics-agents"],
    queryFn: () => analyticsApi.agents(),
  });

  const { data: utilizationData } = useQuery({
    queryKey: ["analytics-utilization"],
    queryFn: () => analyticsApi.workerUtilization(),
    refetchInterval: 15000,
  });

  const overview = overviewData?.data;
  const agents = agentData?.data ?? [];
  const utilization = utilizationData?.data ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <div className="flex gap-2">
          {[7, 14, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setPeriod(d)}
              className={`px-3 py-1.5 rounded-lg text-sm ${
                period === d
                  ? "bg-primary-600 text-white"
                  : "bg-surface-100 text-surface-600 hover:bg-surface-200"
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      {overview && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="card p-5">
            <div className="flex items-center gap-2 text-surface-500 mb-2">
              <Target className="h-4 w-4" />
              <span className="text-xs font-medium uppercase">Success Rate</span>
            </div>
            <p className="text-3xl font-bold text-green-600">
              {overview.tasks.success_rate}%
            </p>
            <p className="text-xs text-surface-400 mt-1">
              {overview.tasks.completed}/{overview.tasks.total} tasks
            </p>
          </div>

          <div className="card p-5">
            <div className="flex items-center gap-2 text-surface-500 mb-2">
              <Clock className="h-4 w-4" />
              <span className="text-xs font-medium uppercase">Avg Time</span>
            </div>
            <p className="text-3xl font-bold">
              {overview.tasks.avg_completion_seconds > 3600
                ? `${Math.round(overview.tasks.avg_completion_seconds / 3600)}h`
                : overview.tasks.avg_completion_seconds > 60
                  ? `${Math.round(overview.tasks.avg_completion_seconds / 60)}m`
                  : `${Math.round(overview.tasks.avg_completion_seconds)}s`}
            </p>
            <p className="text-xs text-surface-400 mt-1">per task completion</p>
          </div>

          <div className="card p-5">
            <div className="flex items-center gap-2 text-surface-500 mb-2">
              <TrendingUp className="h-4 w-4" />
              <span className="text-xs font-medium uppercase">Total Tasks</span>
            </div>
            <p className="text-3xl font-bold">{overview.tasks.total}</p>
            <p className="text-xs text-surface-400 mt-1">
              last {period} days
            </p>
          </div>

          <div className="card p-5">
            <div className="flex items-center gap-2 text-surface-500 mb-2">
              <BarChart3 className="h-4 w-4" />
              <span className="text-xs font-medium uppercase">Files Created</span>
            </div>
            <p className="text-3xl font-bold">{overview.files.total}</p>
            <p className="text-xs text-surface-400 mt-1">
              {overview.files.total_size_bytes > 0
                ? `${(overview.files.total_size_bytes / 1024 / 1024).toFixed(1)} MB`
                : "0 MB"}
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Agent Performance */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold mb-4">Agent Performance</h2>
          {agents.length === 0 ? (
            <p className="text-surface-400 text-sm">No agent data yet</p>
          ) : (
            <div className="space-y-3">
              {agents.map((agent: any) => (
                <div
                  key={agent.id as string}
                  className="flex items-center gap-4 p-3 bg-surface-50 rounded-lg"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium truncate">
                        {agent.name as string}
                      </p>
                      <span className="text-xs text-surface-400">
                        {agent.role as string}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 mt-1">
                      <span className="text-xs text-green-600">
                        {agent.tasks_completed as number} completed
                      </span>
                      <span className="text-xs text-red-500">
                        {agent.tasks_failed as number} failed
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-primary-600">
                      {agent.success_rate as number}%
                    </p>
                    <p className="text-xs text-surface-400">success</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Worker Utilization */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold mb-4">Worker Utilization</h2>
          {utilization.length === 0 ? (
            <p className="text-surface-400 text-sm">No workers online</p>
          ) : (
            <div className="space-y-4">
              {utilization.map((worker: any) => (
                <div key={worker.id as string} className="p-3 bg-surface-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Cpu className="h-4 w-4 text-surface-500" />
                      <span className="text-sm font-medium">
                        {worker.name as string}
                      </span>
                    </div>
                    <span className="text-xs text-surface-400">
                      {worker.agents_busy as number}/{worker.agents_active as number} busy
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-surface-500">CPU</span>
                        <span>{(worker.cpu_percent as number).toFixed(0)}%</span>
                      </div>
                      <div className="w-full bg-surface-200 rounded-full h-1.5">
                        <div
                          className="bg-blue-500 rounded-full h-1.5"
                          style={{ width: `${worker.cpu_percent as number}%` }}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-surface-500">RAM</span>
                        <span>{(worker.memory_percent as number).toFixed(0)}%</span>
                      </div>
                      <div className="w-full bg-surface-200 rounded-full h-1.5">
                        <div
                          className="bg-green-500 rounded-full h-1.5"
                          style={{ width: `${worker.memory_percent as number}%` }}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-surface-500">Capacity</span>
                        <span>{(worker.capacity_percent as number).toFixed(0)}%</span>
                      </div>
                      <div className="w-full bg-surface-200 rounded-full h-1.5">
                        <div
                          className="bg-orange-500 rounded-full h-1.5"
                          style={{ width: `${worker.capacity_percent as number}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
