import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Server, Check, X } from "lucide-react";
import { adminApi } from "../api/endpoints";
import { cn, formatDate } from "../lib/utils";
import toast from "react-hot-toast";

export default function Workers() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["workers"],
    queryFn: () => adminApi.workers(),
    refetchInterval: 10000,
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, approved }: { id: string; approved: boolean }) =>
      adminApi.approveWorker(id, { is_approved: approved }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workers"] });
      toast.success("Worker updated");
    },
  });

  const workers = data?.data ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Workers</h1>
        <div className="text-sm text-surface-500">
          {workers.filter((w: any) => w.status === "online").length} / {workers.length} online
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      ) : workers.length === 0 ? (
        <div className="card p-12 text-center">
          <Server className="h-12 w-12 text-surface-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-surface-700">No workers connected</h3>
          <p className="text-surface-400 mt-1">
            Run <code className="bg-surface-100 px-2 py-0.5 rounded text-xs">curl -sSL http://master-ip:8080/install | bash</code> on a PC to add it.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {workers.map((worker: any) => (
            <div key={worker.id as string} className="card p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <Server className="h-5 w-5 text-surface-600" />
                  <div>
                    <h3 className="font-semibold">{worker.name as string}</h3>
                    <p className="text-xs text-surface-400">{worker.ip_address as string}</p>
                  </div>
                </div>
                <span
                  className={cn(
                    worker.status === "online" ? "badge-green" :
                    worker.status === "pending" ? "badge-yellow" : "badge-red"
                  )}
                >
                  {worker.status as string}
                </span>
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-xs">
                  <span className="text-surface-500">CPU</span>
                  <span>{(worker.cpu_usage_percent as number).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-surface-100 rounded-full h-1.5">
                  <div className="bg-primary-500 rounded-full h-1.5" style={{ width: `${worker.cpu_usage_percent as number}%` }} />
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-surface-500">Memory</span>
                  <span>{(worker.memory_usage_percent as number).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-surface-100 rounded-full h-1.5">
                  <div className="bg-green-500 rounded-full h-1.5" style={{ width: `${worker.memory_usage_percent as number}%` }} />
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-surface-500">Disk</span>
                  <span>{(worker.disk_usage_percent as number).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-surface-100 rounded-full h-1.5">
                  <div className="bg-orange-500 rounded-full h-1.5" style={{ width: `${worker.disk_usage_percent as number}%` }} />
                </div>
              </div>

              {!(worker.is_approved as boolean) && (
                <div className="flex gap-2 pt-3 border-t border-surface-100">
                  <button
                    onClick={() => approveMutation.mutate({ id: worker.id as string, approved: true })}
                    className="btn-primary text-sm flex-1 flex items-center justify-center gap-1"
                  >
                    <Check className="h-3.5 w-3.5" /> Approve
                  </button>
                  <button
                    onClick={() => approveMutation.mutate({ id: worker.id as string, approved: false })}
                    className="btn-danger text-sm flex items-center justify-center gap-1 px-3"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}

              {worker.last_heartbeat && (
                <p className="text-xs text-surface-400 mt-2">
                  Last seen: {formatDate(worker.last_heartbeat as string)}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
