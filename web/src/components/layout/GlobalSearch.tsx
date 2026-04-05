import { useState, useEffect, useRef, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Bot, ListTodo, FolderOpen, BookOpen } from "lucide-react";
import { cn } from "../../lib/utils";

interface SearchItem {
  id: string;
  name: string;
  category: "agent" | "task" | "file" | "knowledge";
  description: string;
  href: string;
}

const MOCK_DATA: SearchItem[] = [
  { id: "a1", name: "Financial Analyst", category: "agent", description: "GPT-4o - Analyzing quarterly reports", href: "/agents" },
  { id: "a2", name: "Research Specialist", category: "agent", description: "Claude 3.5 - Market research pipeline", href: "/agents" },
  { id: "a3", name: "Content Writer", category: "agent", description: "GPT-4o - Blog post generation", href: "/agents" },
  { id: "a4", name: "Executive Assistant", category: "agent", description: "Claude 3.5 - Email management", href: "/agents" },
  { id: "a5", name: "Software Developer", category: "agent", description: "GPT-4o - Code review automation", href: "/agents" },
  { id: "t1", name: "Q1 Revenue Analysis", category: "task", description: "Running - Financial Analyst", href: "/tasks" },
  { id: "t2", name: "Competitor Report Draft", category: "task", description: "Completed - Research Specialist", href: "/tasks" },
  { id: "t3", name: "Weekly Newsletter", category: "task", description: "Pending - Content Writer", href: "/tasks" },
  { id: "t4", name: "Customer Feedback Summary", category: "task", description: "Running - Executive Assistant", href: "/tasks" },
  { id: "t5", name: "Security Audit PR Review", category: "task", description: "Queued - Software Developer", href: "/tasks" },
  { id: "t6", name: "Marketing Campaign Brief", category: "task", description: "Completed - Content Writer", href: "/tasks" },
  { id: "f1", name: "q1-financial-report.pdf", category: "file", description: "2.4 MB - Uploaded 2 days ago", href: "/files" },
  { id: "f2", name: "competitor-analysis.xlsx", category: "file", description: "1.1 MB - Uploaded 5 days ago", href: "/files" },
  { id: "f3", name: "meeting-notes-march.docx", category: "file", description: "340 KB - Uploaded 1 week ago", href: "/files" },
  { id: "f4", name: "product-roadmap-2024.pdf", category: "file", description: "5.8 MB - Uploaded 3 days ago", href: "/files" },
  { id: "k1", name: "Company Style Guide", category: "knowledge", description: "Brand guidelines and tone of voice", href: "/knowledge" },
  { id: "k2", name: "API Documentation v3", category: "knowledge", description: "REST API reference for integrations", href: "/knowledge" },
  { id: "k3", name: "Onboarding Procedures", category: "knowledge", description: "New hire onboarding checklist", href: "/knowledge" },
  { id: "k4", name: "Sales Playbook", category: "knowledge", description: "Objection handling and pitch templates", href: "/knowledge" },
];

const CATEGORY_META: Record<SearchItem["category"], { label: string; icon: typeof Bot }> = {
  agent: { label: "Agents", icon: Bot },
  task: { label: "Tasks", icon: ListTodo },
  file: { label: "Files", icon: FolderOpen },
  knowledge: { label: "Knowledge", icon: BookOpen },
};

export default function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // Listen for Ctrl+K custom event
  useEffect(() => {
    function handleOpen() {
      setOpen(true);
    }
    window.addEventListener("open-search", handleOpen);
    return () => window.removeEventListener("open-search", handleOpen);
  }, []);

  // Also listen for raw Ctrl+K in case shortcuts hook isn't mounted
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery("");
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const results = useMemo(() => {
    if (!query.trim()) return [];
    const q = query.toLowerCase();
    return MOCK_DATA.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q),
    );
  }, [query]);

  const grouped = useMemo(() => {
    const groups: Partial<Record<SearchItem["category"], SearchItem[]>> = {};
    for (const item of results) {
      if (!groups[item.category]) groups[item.category] = [];
      groups[item.category]!.push(item);
    }
    return groups;
  }, [results]);

  function handleSelect(item: SearchItem) {
    setOpen(false);
    navigate(item.href);
  }

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={() => setOpen(false)}>
      <div
        className="w-full max-w-lg bg-white rounded-lg border border-neutral-200 shadow-lg overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        style={{ marginTop: "-10vh" }}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 border-b border-neutral-200">
          <Search className="h-4 w-4 text-neutral-400 flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search agents, tasks, files, knowledge..."
            className="flex-1 py-3 text-sm text-neutral-900 placeholder-neutral-400 outline-none bg-transparent"
          />
          <button
            onClick={() => setOpen(false)}
            className="flex items-center justify-center h-5 px-1.5 rounded bg-neutral-100 border border-neutral-200"
          >
            <span className="text-[10px] font-medium text-neutral-400">ESC</span>
          </button>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto">
          {query.trim() && results.length === 0 && (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-neutral-400">No results for "{query}"</p>
            </div>
          )}

          {(["agent", "task", "file", "knowledge"] as const).map((cat) => {
            const items = grouped[cat];
            if (!items?.length) return null;
            const meta = CATEGORY_META[cat];
            const Icon = meta.icon;

            return (
              <div key={cat}>
                <div className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-neutral-400 bg-neutral-50 border-b border-neutral-100">
                  {meta.label}
                </div>
                {items.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => handleSelect(item)}
                    className={cn(
                      "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors",
                      "hover:bg-neutral-50",
                    )}
                  >
                    <Icon className="h-4 w-4 text-neutral-400 flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-neutral-900 truncate">{item.name}</p>
                      <p className="text-xs text-neutral-400 truncate">{item.description}</p>
                    </div>
                  </button>
                ))}
              </div>
            );
          })}

          {!query.trim() && (
            <div className="px-4 py-8 text-center">
              <p className="text-xs text-neutral-400">Start typing to search across agents, tasks, files, and knowledge.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-neutral-100 bg-neutral-50 flex items-center gap-4">
          <span className="text-[10px] text-neutral-400">
            <kbd className="px-1 py-0.5 rounded bg-white border border-neutral-200 text-[10px] font-medium">↑↓</kbd> Navigate
          </span>
          <span className="text-[10px] text-neutral-400">
            <kbd className="px-1 py-0.5 rounded bg-white border border-neutral-200 text-[10px] font-medium">↵</kbd> Open
          </span>
          <span className="text-[10px] text-neutral-400">
            <kbd className="px-1 py-0.5 rounded bg-white border border-neutral-200 text-[10px] font-medium">Esc</kbd> Close
          </span>
        </div>
      </div>
    </div>
  );
}
