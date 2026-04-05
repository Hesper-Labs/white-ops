import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X as XIcon } from "lucide-react";
import { tasksApi, agentsApi } from "../api/endpoints";
import { cn, formatDate } from "../lib/utils";
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

const priorityColors: Record<string, string> = {
  critical: "text-red-600 font-bold",
  high: "text-orange-600",
  medium: "text-surface-600",
  low: "text-surface-400",
};

export default function Tasks() {
  const [showCreate, setShowCreate] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["tasks", statusFilter],
    queryFn: () => tasksApi.list(statusFilter ? { status_filter: statusFilter } : undefined),
    refetchInterval: 5000,
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => tasksApi.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      toast.success("Task cancelled");
    },
  });

  const tasks = data?.data ?? [];
  const statuses = ["", "pending", "assigned", "in_progress", "review", "completed", "failed"];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Tasks</h1>
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4" />
          New Task
        </button>
      </div>

      <div className="flex gap-2 mb-4 flex-wrap">
        {statuses.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-sm transition-colors",
              statusFilter === s
                ? "bg-primary-600 text-white"
                : "bg-surface-100 text-surface-600 hover:bg-surface-200",
            )}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="bg-surface-50 border-b border-surface-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-medium text-surface-500 uppercase">Title</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-surface-500 uppercase">Status</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-surface-500 uppercase">Priority</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-surface-500 uppercase">Created</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-surface-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {tasks.map((task: any) => (
                <tr key={task.id as string} className="hover:bg-surface-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-sm">{task.title as string}</p>
                    {task.description && (
                      <p className="text-xs text-surface-400 mt-0.5 truncate max-w-md">{task.description as string}</p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={statusColors[(task.status as string)] ?? "badge-gray"}>
                      {(task.status as string).replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn("text-sm capitalize", priorityColors[(task.priority as string)] ?? "")}>
                      {task.priority as string}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-surface-500">
                    {formatDate(task.created_at as string)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {!["completed", "cancelled", "failed"].includes(task.status as string) && (
                      <button
                        onClick={() => cancelMutation.mutate(task.id as string)}
                        className="text-surface-400 hover:text-red-500"
                        title="Cancel"
                      >
                        <XIcon className="h-4 w-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {tasks.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center text-surface-400">
                    No tasks found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && <CreateTaskModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function CreateTaskModal({ onClose }: { onClose: () => void }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [priority, setPriority] = useState("medium");
  const [agentId, setAgentId] = useState("");
  const queryClient = useQueryClient();

  const { data: agentsData } = useQuery({
    queryKey: ["agents"],
    queryFn: () => agentsApi.list(),
  });

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => tasksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      toast.success("Task created");
      onClose();
    },
    onError: () => toast.error("Failed to create task"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      title,
      description,
      instructions,
      priority,
      agent_id: agentId || undefined,
    });
  };

  const agents = agentsData?.data ?? [];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="card p-6 w-full max-w-lg">
        <h2 className="text-lg font-semibold mb-4">Create New Task</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Title</label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea className="input" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Instructions</label>
            <textarea
              className="input"
              rows={4}
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Detailed instructions for the agent..."
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Priority</label>
              <select className="input" value={priority} onChange={(e) => setPriority(e.target.value)}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Assign to Agent</label>
              <select className="input" value={agentId} onChange={(e) => setAgentId(e.target.value)}>
                <option value="">Auto-assign</option>
                {agents.map((a: any) => (
                  <option key={a.id as string} value={a.id as string}>{a.name as string}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
            <button type="submit" className="btn-primary flex-1" disabled={mutation.isPending}>
              {mutation.isPending ? "Creating..." : "Create Task"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
