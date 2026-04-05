import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Users, Plus, MessageCircle, CheckCircle } from "lucide-react";
import { collaborationApi, agentsApi } from "../api/endpoints";
import { formatDate } from "../lib/utils";
import toast from "react-hot-toast";

export default function Collaboration() {
  const [showCreate, setShowCreate] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["collaborations"],
    queryFn: () => collaborationApi.list(),
    refetchInterval: 5000,
  });

  const { data: detailData } = useQuery({
    queryKey: ["collaboration-detail", selectedId],
    queryFn: () => (selectedId ? collaborationApi.get(selectedId) : null),
    enabled: !!selectedId,
    refetchInterval: 3000,
  });

  const closeMutation = useMutation({
    mutationFn: (id: string) => collaborationApi.close(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["collaborations"] });
      toast.success("Collaboration closed");
    },
  });

  const collaborations = data?.data ?? [];
  const detail = detailData?.data;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Agent Collaboration</h1>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={() => setShowCreate(true)}
        >
          <Plus className="h-4 w-4" />
          New Session
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sessions List */}
          <div className="space-y-3">
            {collaborations.length === 0 ? (
              <div className="card p-8 text-center">
                <Users className="h-10 w-10 text-surface-300 mx-auto mb-3" />
                <p className="text-surface-500 text-sm">
                  No collaboration sessions yet
                </p>
              </div>
            ) : (
              collaborations.map((c: any) => (
                <div
                  key={c.id as string}
                  onClick={() => setSelectedId(c.id as string)}
                  className={`card p-4 cursor-pointer transition-colors ${
                    selectedId === c.id
                      ? "border-primary-500 ring-1 ring-primary-500"
                      : "hover:border-surface-300"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-medium text-sm">{c.name as string}</h3>
                    <span
                      className={
                        c.status === "active" ? "badge-green" : "badge-gray"
                      }
                    >
                      {c.status as string}
                    </span>
                  </div>
                  <p className="text-xs text-surface-400">
                    {(c.participants as string[]).length} agents |{" "}
                    {c.message_count as number} messages
                  </p>
                  <p className="text-xs text-surface-300 mt-1">
                    {formatDate(c.created_at as string)}
                  </p>
                </div>
              ))
            )}
          </div>

          {/* Session Detail */}
          <div className="lg:col-span-2">
            {detail ? (
              <div className="card p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold">{detail.name}</h2>
                    {detail.description && (
                      <p className="text-sm text-surface-500">
                        {detail.description}
                      </p>
                    )}
                  </div>
                  {detail.status === "active" && (
                    <button
                      onClick={() => closeMutation.mutate(detail.id)}
                      className="btn-secondary text-sm flex items-center gap-1"
                    >
                      <CheckCircle className="h-3.5 w-3.5" /> Close
                    </button>
                  )}
                </div>

                {/* Participants */}
                <div className="flex gap-2 mb-4">
                  {(detail.participants as string[]).map(
                    (pid: string, i: number) => (
                      <span
                        key={pid}
                        className="badge-blue text-xs"
                      >
                        Agent {i + 1}
                      </span>
                    ),
                  )}
                </div>

                {/* Shared Context */}
                {detail.shared_context &&
                  Object.keys(detail.shared_context).length > 0 && (
                    <div className="bg-surface-50 rounded-lg p-3 mb-4">
                      <p className="text-xs font-medium text-surface-500 mb-1">
                        Shared Context
                      </p>
                      <pre className="text-xs text-surface-600 whitespace-pre-wrap">
                        {JSON.stringify(detail.shared_context, null, 2)}
                      </pre>
                    </div>
                  )}

                {/* Messages */}
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {(detail.messages as Array<Record<string, string>>)?.length === 0 ? (
                    <p className="text-center text-surface-400 text-sm py-8">
                      No messages in this session yet
                    </p>
                  ) : (
                    (
                      detail.messages as Array<Record<string, string>>
                    )?.map((msg, i: number) => (
                      <div
                        key={i}
                        className="flex gap-3 p-3 bg-surface-50 rounded-lg"
                      >
                        <div className="h-7 w-7 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
                          <MessageCircle className="h-3.5 w-3.5 text-primary-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium">
                              {msg.agent_id?.slice(0, 8)}...
                            </span>
                            <span className="badge-gray text-xs">
                              {msg.type}
                            </span>
                            <span className="text-xs text-surface-300">
                              {msg.timestamp}
                            </span>
                          </div>
                          <p className="text-sm text-surface-700 mt-1">
                            {msg.message}
                          </p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ) : (
              <div className="card p-12 text-center">
                <Users className="h-10 w-10 text-surface-300 mx-auto mb-3" />
                <p className="text-surface-400 text-sm">
                  Select a collaboration session to view details
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {showCreate && <CreateCollaborationModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function CreateCollaborationModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const queryClient = useQueryClient();

  const { data: agentsData } = useQuery({
    queryKey: ["agents"],
    queryFn: () => agentsApi.list(),
  });

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => collaborationApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["collaborations"] });
      toast.success("Collaboration session created");
      onClose();
    },
  });

  const agents = agentsData?.data ?? [];

  const toggleAgent = (id: string) => {
    setSelectedAgents((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id],
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="card p-6 w-full max-w-md">
        <h2 className="text-lg font-semibold mb-4">New Collaboration Session</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            mutation.mutate({ name, description, participants: selectedAgents });
          }}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium mb-1">Session Name</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea className="input" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">
              Participating Agents ({selectedAgents.length} selected)
            </label>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {agents.map((a: any) => (
                <label
                  key={a.id as string}
                  className="flex items-center gap-2 p-2 rounded-lg hover:bg-surface-50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedAgents.includes(a.id as string)}
                    onChange={() => toggleAgent(a.id as string)}
                    className="h-4 w-4 text-primary-600 rounded"
                  />
                  <span className="text-sm">{a.name as string}</span>
                  <span className="text-xs text-surface-400">{a.role as string}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
            <button
              type="submit"
              className="btn-primary flex-1"
              disabled={selectedAgents.length < 2 || mutation.isPending}
            >
              {mutation.isPending ? "Creating..." : "Create Session"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
