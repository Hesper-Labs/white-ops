import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Brain,
  Search,
  Plus,
  Trash2,
  Edit3,
  Eye,
  Download,
  X,
  Database,
  Tag,
  Clock,
  Star,
  Filter,
} from "lucide-react";
import { agentMemoryApi, agentsApi } from "../api/endpoints";
import { cn, formatDate, formatBytes } from "../lib/utils";
import toast from "react-hot-toast";

// --- Demo Data ---

const DEMO_AGENTS = [
  { id: "a1", name: "Research Agent" },
  { id: "a2", name: "Report Writer" },
  { id: "a3", name: "Code Reviewer" },
  { id: "a4", name: "Data Analyst" },
  { id: "a5", name: "HR Coordinator" },
];

const DEMO_MEMORIES: Record<string, any[]> = {
  a1: [
    { id: "m1", content: "User prefers detailed analysis with citations from peer-reviewed sources. Always include methodology section.", category: "preference", importance: 9, created_at: "2025-04-01T10:00:00Z", tokens: 245 },
    { id: "m2", content: "Project Alpha deadline is Q2 2025. Key stakeholders: Sarah (PM), Mike (Engineering Lead), John (Design).", category: "project", importance: 8, created_at: "2025-03-28T14:30:00Z", tokens: 312 },
    { id: "m3", content: "The competitor analysis template should follow the SWOT framework with market sizing data from Statista.", category: "template", importance: 7, created_at: "2025-03-25T09:15:00Z", tokens: 189 },
    { id: "m4", content: "Turkish market reports should be formatted in Turkish locale with TRY currency. Date format: DD.MM.YYYY.", category: "localization", importance: 6, created_at: "2025-03-20T11:00:00Z", tokens: 156 },
    { id: "m5", content: "When generating reports, always include an executive summary of no more than 200 words at the beginning.", category: "preference", importance: 8, created_at: "2025-04-03T16:45:00Z", tokens: 178 },
    { id: "m6", content: "Previous research on AI governance frameworks identified 12 key regulatory bodies across EU, US, and APAC regions.", category: "research", importance: 5, created_at: "2025-03-15T08:30:00Z", tokens: 892 },
  ],
  a2: [
    { id: "m7", content: "Report formatting: Use company branding guidelines v2.3. Primary color: #1a1a2e, Font: Inter.", category: "style", importance: 9, created_at: "2025-04-02T10:00:00Z", tokens: 134 },
    { id: "m8", content: "Sales reports require sign-off from VP of Sales before distribution. Contact: vp-sales@company.com.", category: "workflow", importance: 8, created_at: "2025-03-30T11:00:00Z", tokens: 98 },
  ],
  a3: [
    { id: "m9", content: "Code review standards: Follow ESLint config from .eslintrc.json. TypeScript strict mode required.", category: "standards", importance: 9, created_at: "2025-04-01T09:00:00Z", tokens: 167 },
  ],
};

const CATEGORIES = ["preference", "project", "template", "localization", "research", "style", "workflow", "standards"];

const categoryColors: Record<string, string> = {
  preference: "bg-blue-100 text-blue-700",
  project: "bg-purple-100 text-purple-700",
  template: "bg-green-100 text-green-700",
  localization: "bg-amber-100 text-amber-700",
  research: "bg-indigo-100 text-indigo-700",
  style: "bg-pink-100 text-pink-700",
  workflow: "bg-cyan-100 text-cyan-700",
  standards: "bg-orange-100 text-orange-700",
};

// --- Component ---

export default function AgentMemory() {
  const [selectedAgent, setSelectedAgent] = useState("a1");
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [selectedMemory, setSelectedMemory] = useState<any>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newMemory, setNewMemory] = useState({ content: "", category: "preference", importance: 5 });
  const queryClient = useQueryClient();

  const { data: agentsData } = useQuery({
    queryKey: ["agents-list"],
    queryFn: async () => {
      try {
        const res = await agentsApi.list();
        return res.data;
      } catch {
        return DEMO_AGENTS;
      }
    },
  });

  const agents = (Array.isArray(agentsData) ? agentsData : agentsData?.data ?? DEMO_AGENTS) as any[];

  const { data: memoriesData } = useQuery({
    queryKey: ["agent-memories", selectedAgent],
    queryFn: async () => {
      try {
        const res = await agentMemoryApi.getMemories(selectedAgent);
        return res.data;
      } catch {
        return DEMO_MEMORIES[selectedAgent] ?? [];
      }
    },
  });

  const memories = (Array.isArray(memoriesData) ? memoriesData : memoriesData?.data ?? DEMO_MEMORIES[selectedAgent] ?? []) as any[];

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      agentMemoryApi.createMemory(selectedAgent, data).catch(() => Promise.resolve()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-memories"] });
      toast.success("Memory created");
      setShowCreateModal(false);
      setNewMemory({ content: "", category: "preference", importance: 5 });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      agentMemoryApi.deleteMemory(id).catch(() => Promise.resolve()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-memories"] });
      toast.success("Memory deleted");
    },
  });

  const clearAllMutation = useMutation({
    mutationFn: () =>
      agentMemoryApi.clearAll(selectedAgent).catch(() => Promise.resolve()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-memories"] });
      toast.success("All memories cleared");
    },
  });

  const filtered = memories.filter((m: any) => {
    const matchesSearch = !searchQuery || m.content.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !categoryFilter || m.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const totalTokens = memories.reduce((s: number, m: any) => s + (m.tokens ?? 0), 0);
  const categories = [...new Set(memories.map((m: any) => m.category))];
  const storageUsed = totalTokens * 4; // rough bytes estimate
  const lastUpdated = memories.length > 0
    ? memories.reduce((latest: string, m: any) => m.created_at > latest ? m.created_at : latest, memories[0].created_at)
    : null;

  const currentAgentName = agents.find((a: any) => a.id === selectedAgent)?.name ?? "Unknown";

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-neutral-900 dark:text-white">Agent Memory</h1>
          <p className="text-xs text-neutral-400 mt-0.5">Manage context and learned information for each agent</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const blob = new Blob([JSON.stringify(memories, null, 2)], { type: "application/json" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `${currentAgentName.replace(/\s+/g, "-").toLowerCase()}-memories.json`;
              a.click();
              URL.revokeObjectURL(url);
              toast.success("Memories exported");
            }}
            className="btn-secondary text-sm flex items-center gap-1.5"
          >
            <Download className="h-3.5 w-3.5" /> Export
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary text-sm flex items-center gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" /> Add Memory
          </button>
        </div>
      </div>

      {/* Agent Selector */}
      <div className="mb-6">
        <label className="text-xs font-medium text-neutral-700 mb-1.5 block">Select Agent</label>
        <select
          className="input w-64"
          value={selectedAgent}
          onChange={(e) => { setSelectedAgent(e.target.value); setSearchQuery(""); setCategoryFilter(""); }}
        >
          {agents.map((agent: any) => (
            <option key={agent.id} value={agent.id}>{agent.name}</option>
          ))}
        </select>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="card p-5">
          <div className="flex items-center gap-2 text-neutral-500 mb-2">
            <Brain className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Total Memories</span>
          </div>
          <p className="text-3xl font-bold">{memories.length}</p>
          <p className="text-xs text-neutral-400 mt-1">{currentAgentName}</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 text-neutral-500 mb-2">
            <Tag className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Categories</span>
          </div>
          <p className="text-3xl font-bold">{categories.length}</p>
          <p className="text-xs text-neutral-400 mt-1">distinct categories</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 text-neutral-500 mb-2">
            <Database className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Storage Used</span>
          </div>
          <p className="text-3xl font-bold">{formatBytes(storageUsed)}</p>
          <p className="text-xs text-neutral-400 mt-1">{totalTokens.toLocaleString()} tokens</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 text-neutral-500 mb-2">
            <Clock className="h-4 w-4" />
            <span className="text-xs font-medium uppercase">Last Updated</span>
          </div>
          <p className="text-lg font-bold">{lastUpdated ? formatDate(lastUpdated) : "-"}</p>
          <p className="text-xs text-neutral-400 mt-1">most recent entry</p>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-md">
          <Search className="h-4 w-4 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            className="input w-full pl-9"
            placeholder="Search memories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-neutral-400 dark:text-neutral-500" />
          <select
            className="input w-40"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => clearAllMutation.mutate()}
          className="text-xs text-red-600 hover:text-red-700 font-medium ml-auto"
        >
          Clear All Memories
        </button>
      </div>

      {/* Memory Cards */}
      {filtered.length === 0 ? (
        <div className="card p-12 text-center">
          <Brain className="h-12 w-12 text-neutral-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-neutral-700 dark:text-neutral-300">No memories found</h3>
          <p className="text-sm text-neutral-400 mt-1">
            {memories.length === 0
              ? "This agent has no stored memories yet"
              : "No memories match your search criteria"}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((memory: any) => (
            <div key={memory.id} className="card p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full", categoryColors[memory.category] ?? "bg-neutral-100 text-neutral-600")}>
                  {memory.category}
                </span>
                <div className="flex items-center gap-0.5">
                  {Array.from({ length: 5 }, (_, i) => (
                    <Star
                      key={i}
                      className={cn(
                        "h-3 w-3",
                        i < Math.ceil(memory.importance / 2)
                          ? "text-amber-400 fill-amber-400"
                          : "text-neutral-200"
                      )}
                    />
                  ))}
                </div>
              </div>

              <p className="text-xs text-neutral-700 leading-relaxed line-clamp-3 mb-3">
                {memory.content}
              </p>

              <div className="flex items-center justify-between pt-3 border-t border-neutral-100">
                <span className="text-[10px] text-neutral-400 dark:text-neutral-500">
                  {formatDate(memory.created_at)}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setSelectedMemory(memory)}
                    className="p-1 rounded hover:bg-neutral-100 text-neutral-400 hover:text-neutral-600"
                    title="View"
                  >
                    <Eye className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => { setNewMemory({ content: memory.content, category: memory.category, importance: memory.importance }); setShowCreateModal(true); }}
                    className="p-1 rounded hover:bg-neutral-100 text-neutral-400 hover:text-neutral-600"
                    title="Edit"
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => deleteMutation.mutate(memory.id)}
                    className="p-1 rounded hover:bg-red-50 text-neutral-400 hover:text-red-600"
                    title="Delete"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* View Memory Modal */}
      {selectedMemory && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setSelectedMemory(null)}>
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-5 border-b border-neutral-100">
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />
                <h2 className="text-sm font-bold text-neutral-900 dark:text-white">Memory Details</h2>
              </div>
              <button onClick={() => setSelectedMemory(null)} className="p-1 rounded hover:bg-neutral-100">
                <X className="h-4 w-4 text-neutral-400 dark:text-neutral-500" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full", categoryColors[selectedMemory.category] ?? "bg-neutral-100 text-neutral-600")}>
                  {selectedMemory.category}
                </span>
              </div>
              <p className="text-sm text-neutral-700 leading-relaxed whitespace-pre-wrap">{selectedMemory.content}</p>
              <div className="grid grid-cols-3 gap-4 bg-neutral-50 rounded-lg p-3">
                <div>
                  <span className="text-[10px] text-neutral-400 uppercase">Importance</span>
                  <p className="text-xs font-medium">{selectedMemory.importance}/10</p>
                </div>
                <div>
                  <span className="text-[10px] text-neutral-400 uppercase">Tokens</span>
                  <p className="text-xs font-medium">{selectedMemory.tokens?.toLocaleString() ?? "-"}</p>
                </div>
                <div>
                  <span className="text-[10px] text-neutral-400 uppercase">Created</span>
                  <p className="text-xs font-medium">{formatDate(selectedMemory.created_at)}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create/Edit Memory Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setShowCreateModal(false)}>
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
            <div className="p-5 border-b border-neutral-100">
              <h2 className="text-sm font-bold text-neutral-900 dark:text-white">
                {newMemory.content ? "Edit Memory" : "Create Memory"}
              </h2>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="text-xs font-medium text-neutral-700 mb-1 block">Category</label>
                <select
                  className="input w-full"
                  value={newMemory.category}
                  onChange={(e) => setNewMemory({ ...newMemory, category: e.target.value })}
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-neutral-700 mb-1 block">Content</label>
                <textarea
                  className="input w-full h-32 resize-none"
                  placeholder="Enter memory content..."
                  value={newMemory.content}
                  onChange={(e) => setNewMemory({ ...newMemory, content: e.target.value })}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-neutral-700 mb-1 block">
                  Importance: {newMemory.importance}/10
                </label>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={newMemory.importance}
                  onChange={(e) => setNewMemory({ ...newMemory, importance: +e.target.value })}
                  className="w-full"
                />
                <div className="flex justify-between text-[10px] text-neutral-400 dark:text-neutral-500">
                  <span>Low</span>
                  <span>High</span>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 p-5 border-t border-neutral-100">
              <button onClick={() => setShowCreateModal(false)} className="btn-secondary text-sm">Cancel</button>
              <button
                onClick={() => createMutation.mutate(newMemory)}
                disabled={!newMemory.content}
                className="btn-primary text-sm flex items-center gap-1.5"
              >
                <Plus className="h-3.5 w-3.5" /> Save Memory
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
