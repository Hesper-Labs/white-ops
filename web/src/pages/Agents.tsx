import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Play, Square, Trash2, Bot } from "lucide-react";
import { agentsApi } from "../api/endpoints";
import { formatDate } from "../lib/utils";
import toast from "react-hot-toast";

const statusMap: Record<string, { badge: string; dot: string }> = {
  idle: { badge: "badge-green", dot: "online" },
  busy: { badge: "badge-yellow", dot: "busy" },
  error: { badge: "badge-red", dot: "error" },
  offline: { badge: "badge-gray", dot: "offline" },
  paused: { badge: "badge-blue", dot: "offline" },
};

export default function Agents() {
  const [showCreate, setShowCreate] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({ queryKey: ["agents"], queryFn: () => agentsApi.list(), refetchInterval: 5000 });
  const startMut = useMutation({ mutationFn: (id: string) => agentsApi.start(id), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["agents"] }); toast.success("Agent started"); } });
  const stopMut = useMutation({ mutationFn: (id: string) => agentsApi.stop(id), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["agents"] }); toast.success("Agent stopped"); } });
  const deleteMut = useMutation({ mutationFn: (id: string) => agentsApi.delete(id), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["agents"] }); toast.success("Agent deleted"); } });

  const agents = data?.data ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-neutral-900 dark:text-white">Agents</h1>
          <p className="text-xs text-neutral-400 mt-0.5">{agents.length} agents configured</p>
        </div>
        <button className="btn-primary flex items-center gap-1.5" onClick={() => setShowCreate(true)}>
          <Plus className="h-3.5 w-3.5" /> New Agent
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64"><div className="w-6 h-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin" /></div>
      ) : agents.length === 0 ? (
        <div className="card p-12 text-center">
          <Bot className="h-10 w-10 text-neutral-300 mx-auto mb-3" />
          <p className="text-sm font-medium text-neutral-600">No agents configured</p>
          <p className="text-xs text-neutral-400 mt-1">Create your first AI agent to get started.</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr>
                <th className="table-header">Agent</th>
                <th className="table-header">Role</th>
                <th className="table-header">Status</th>
                <th className="table-header">LLM</th>
                <th className="table-header text-right">Completed</th>
                <th className="table-header text-right">Failed</th>
                <th className="table-header text-right">Created</th>
                <th className="table-header w-24">Actions</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent: any) => {
                const st = statusMap[agent.status as string] ?? { badge: "badge-gray", dot: "offline" };
                return (
                  <tr key={agent.id} className="border-b border-neutral-100 hover:bg-neutral-50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className={`status-dot ${st.dot}`} />
                        <div>
                          <p className="text-sm font-semibold text-neutral-900 dark:text-white">{agent.name}</p>
                          {agent.description && <p className="text-xs text-neutral-400 mt-0.5 max-w-xs truncate">{agent.description}</p>}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3"><span className="text-xs font-medium text-neutral-600 capitalize">{agent.role}</span></td>
                    <td className="px-4 py-3"><span className={st.badge}>{agent.status}</span></td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{agent.llm_provider}</span>
                      <span className="text-xs text-neutral-300 mx-1">/</span>
                      <span className="text-xs text-neutral-500 font-mono">{String(agent.llm_model).split("/").pop()?.slice(0, 20)}</span>
                    </td>
                    <td className="px-4 py-3 text-right"><span className="text-sm font-medium text-emerald-600">{agent.tasks_completed}</span></td>
                    <td className="px-4 py-3 text-right"><span className="text-sm font-medium text-red-500">{agent.tasks_failed}</span></td>
                    <td className="px-4 py-3 text-right text-xs text-neutral-400 dark:text-neutral-500">{formatDate(agent.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 justify-end">
                        {agent.status === "offline" || agent.status === "paused" ? (
                          <button onClick={() => startMut.mutate(agent.id)} className="btn-ghost" title="Start"><Play className="h-3.5 w-3.5" /></button>
                        ) : (
                          <button onClick={() => stopMut.mutate(agent.id)} className="btn-ghost" title="Stop"><Square className="h-3.5 w-3.5" /></button>
                        )}
                        <button onClick={() => deleteMut.mutate(agent.id)} className="btn-ghost text-red-400 hover:text-red-600" title="Delete"><Trash2 className="h-3.5 w-3.5" /></button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && <CreateAgentModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function CreateAgentModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [role, setRole] = useState("general");
  const [llmProvider, setLlmProvider] = useState("anthropic");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => agentsApi.create(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["agents"] }); toast.success("Agent created"); onClose(); },
    onError: () => toast.error("Failed to create agent"),
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="card p-6 w-full max-w-md shadow-lg" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-sm font-bold text-neutral-900 mb-4">Create Agent</h2>
        <form onSubmit={(e) => { e.preventDefault(); mutation.mutate({ name, description, role, llm_provider: llmProvider }); }} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-neutral-500 mb-1">Name</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} required placeholder="Research Agent" />
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-500 mb-1">Description</label>
            <input className="input" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What this agent does" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1">Role</label>
              <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="general">General</option>
                <option value="researcher">Researcher</option>
                <option value="analyst">Data Analyst</option>
                <option value="writer">Writer</option>
                <option value="developer">Developer</option>
                <option value="assistant">Executive Assistant</option>
                <option value="accountant">Accountant</option>
                <option value="hr">HR Specialist</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1">LLM Provider</label>
              <select className="input" value={llmProvider} onChange={(e) => setLlmProvider(e.target.value)}>
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="openai">OpenAI (GPT)</option>
                <option value="google">Google (Gemini)</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>
          </div>
          <div className="flex gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
            <button type="submit" className="btn-primary flex-1" disabled={mutation.isPending}>{mutation.isPending ? "Creating..." : "Create"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
