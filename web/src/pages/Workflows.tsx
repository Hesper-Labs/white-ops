import { useQuery } from "@tanstack/react-query";
import { GitBranch, Plus } from "lucide-react";
import { workflowsApi } from "../api/endpoints";
import { formatDate } from "../lib/utils";

export default function Workflows() {
  const { data, isLoading } = useQuery({
    queryKey: ["workflows"],
    queryFn: () => workflowsApi.list(),
  });

  const workflows = data?.data ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Workflows</h1>
        <button className="btn-primary flex items-center gap-2">
          <Plus className="h-4 w-4" />
          New Workflow
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      ) : workflows.length === 0 ? (
        <div className="card p-12 text-center">
          <GitBranch className="h-12 w-12 text-surface-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-surface-700">No workflows yet</h3>
          <p className="text-surface-400 mt-1">Create multi-step automated workflows with the visual builder.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {workflows.map((wf: any) => (
            <div key={wf.id as string} className="card p-5">
              <div className="flex items-center gap-3 mb-2">
                <GitBranch className="h-5 w-5 text-primary-600" />
                <h3 className="font-semibold">{wf.name as string}</h3>
              </div>
              {wf.description && <p className="text-sm text-surface-500 mb-3">{wf.description as string}</p>}
              <div className="flex items-center justify-between text-xs text-surface-400">
                <span className={wf.status === "active" ? "badge-green" : "badge-gray"}>
                  {wf.status as string}
                </span>
                <span>{formatDate(wf.created_at as string)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
