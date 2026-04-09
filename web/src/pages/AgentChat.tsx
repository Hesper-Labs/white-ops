import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Plus,
  Search,
  Send,
  Bot,
  User,
  ChevronDown,
  ChevronRight,
  Paperclip,
  Trash2,
  DollarSign,
  Loader2,
  MessageSquare,
  Wrench,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { agentsApi, chatApi } from "../api/endpoints";
import { cn, formatDate } from "../lib/utils";
import toast from "react-hot-toast";

// ---------- Types ----------

interface DemoAgent {
  id: string;
  name: string;
  status: string;
  llm_model: string;
  role: string;
}

interface DemoConversation {
  id: string;
  title: string;
  agent_id: string;
  agent_name: string;
  last_message: string;
  last_message_at: string;
  total_cost_usd: number;
}

interface ChatMsg {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  tool_calls?: ToolCall[] | null;
  tool_results?: Record<string, unknown> | null;
  tokens_used?: number;
  cost_usd?: number;
  created_at: string;
}

interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result?: string;
  status: "success" | "error" | "running";
  duration?: string;
}

// ---------- Demo Data ----------

const DEMO_AGENTS: DemoAgent[] = [
  { id: "agent-001", name: "Research Agent", status: "idle", llm_model: "claude-sonnet-4-20250514", role: "researcher" },
  { id: "agent-002", name: "Data Analyst", status: "busy", llm_model: "gpt-4o", role: "analyst" },
  { id: "agent-003", name: "Office Assistant", status: "idle", llm_model: "claude-sonnet-4-20250514", role: "assistant" },
  { id: "agent-004", name: "Developer Bot", status: "offline", llm_model: "claude-sonnet-4-20250514", role: "developer" },
];

const DEMO_CONVERSATIONS: DemoConversation[] = [
  {
    id: "conv-001",
    title: "Q1 Market Research",
    agent_id: "agent-001",
    agent_name: "Research Agent",
    last_message: "I've completed the competitor analysis. The report has been saved to your files.",
    last_message_at: "2026-04-08T14:30:00Z",
    total_cost_usd: 0.42,
  },
  {
    id: "conv-002",
    title: "Revenue Data Analysis",
    agent_id: "agent-002",
    agent_name: "Data Analyst",
    last_message: "The pivot table is ready. Revenue grew 23% QoQ across all regions.",
    last_message_at: "2026-04-08T11:15:00Z",
    total_cost_usd: 0.18,
  },
  {
    id: "conv-003",
    title: "Meeting Notes Summary",
    agent_id: "agent-003",
    agent_name: "Office Assistant",
    last_message: "Here's the summary of today's standup meeting with action items highlighted.",
    last_message_at: "2026-04-07T16:45:00Z",
    total_cost_usd: 0.05,
  },
];

const DEMO_MESSAGES: Record<string, ChatMsg[]> = {
  "conv-001": [
    {
      id: "msg-001", role: "user", content: "Can you research the top 5 competitors in the B2B SaaS market and create a pricing comparison?",
      created_at: "2026-04-08T14:00:00Z",
    },
    {
      id: "msg-002", role: "assistant",
      content: "I'll research the top B2B SaaS competitors and compile a pricing comparison for you. Let me start by searching for the latest market data.",
      tool_calls: [
        { name: "web_search", args: { query: "top B2B SaaS competitors 2026 pricing" }, result: "Found 15 relevant results from Gartner, G2, and industry reports.", status: "success", duration: "1.2s" },
        { name: "browser", args: { url: "https://competitor-a.com/pricing" }, result: "Page loaded successfully. Extracted 3 pricing tiers.", status: "success", duration: "2.8s" },
        { name: "web_scraper", args: { selector: ".pricing-table", format: "json" }, result: "Scraped pricing data for 5 competitors.", status: "success", duration: "1.5s" },
      ],
      tokens_used: 2450,
      cost_usd: 0.12,
      created_at: "2026-04-08T14:02:00Z",
    },
    {
      id: "msg-003", role: "assistant",
      content: "I've gathered pricing data from all 5 competitors. Now let me create the comparison spreadsheet and analysis report.",
      tool_calls: [
        { name: "excel", args: { action: "create", filename: "competitor_pricing_matrix.xlsx" }, result: "Created spreadsheet with 3 sheets: Overview, Detailed Comparison, Feature Matrix", status: "success", duration: "2.1s" },
        { name: "data_visualization", args: { chart: "bar", data: "pricing_comparison" }, result: "Generated price_comparison_chart.png", status: "success", duration: "1.8s" },
        { name: "pdf", args: { template: "report", filename: "market_analysis.pdf" }, result: "Generated 8-page analysis report", status: "success", duration: "4.2s" },
      ],
      tokens_used: 1800,
      cost_usd: 0.09,
      created_at: "2026-04-08T14:10:00Z",
    },
    {
      id: "msg-004", role: "user", content: "Great work! Can you also add annual pricing to the comparison?",
      created_at: "2026-04-08T14:15:00Z",
    },
    {
      id: "msg-005", role: "assistant",
      content: "I've completed the competitor analysis. The report has been saved to your files. The comparison now includes both monthly and annual pricing across all 5 competitors. Key findings:\n\n- Competitor A offers the steepest annual discount (30%)\n- Competitor C has the most competitive enterprise tier\n- Our pricing is well-positioned in the mid-market segment\n\nAll files have been saved to the shared drive.",
      tool_calls: [
        { name: "excel", args: { action: "update", filename: "competitor_pricing_matrix.xlsx", sheet: "Annual Pricing" }, result: "Added annual pricing sheet with discount calculations", status: "success", duration: "1.4s" },
        { name: "internal_email", args: { to: "admin", subject: "Market Research Complete" }, result: "Email sent successfully", status: "success", duration: "0.6s" },
      ],
      tokens_used: 3200,
      cost_usd: 0.21,
      created_at: "2026-04-08T14:30:00Z",
    },
  ],
  "conv-002": [
    {
      id: "msg-010", role: "user", content: "Analyze the Q1 revenue data from the sales database and create a summary report.",
      created_at: "2026-04-08T10:00:00Z",
    },
    {
      id: "msg-011", role: "assistant",
      content: "I'll pull the Q1 revenue data and create an analysis. Let me query the database first.",
      tool_calls: [
        { name: "database_query", args: { query: "SELECT region, SUM(revenue) FROM sales WHERE quarter='Q1' GROUP BY region" }, result: "Retrieved 8 region records", status: "success", duration: "0.8s" },
        { name: "data_analysis", args: { operation: "pivot_table", metrics: ["revenue", "growth"] }, result: "Pivot table generated with QoQ comparison", status: "success", duration: "3.2s" },
      ],
      tokens_used: 1200,
      cost_usd: 0.08,
      created_at: "2026-04-08T10:05:00Z",
    },
    {
      id: "msg-012", role: "assistant",
      content: "The pivot table is ready. Revenue grew 23% QoQ across all regions. The North America region led growth at 31%, while APAC showed the strongest acceleration trend. I've saved the detailed report to your files.",
      tokens_used: 800,
      cost_usd: 0.10,
      created_at: "2026-04-08T11:15:00Z",
    },
  ],
  "conv-003": [
    {
      id: "msg-020", role: "system", content: "Conversation started with Office Assistant.",
      created_at: "2026-04-07T16:30:00Z",
    },
    {
      id: "msg-021", role: "user", content: "Summarize today's standup meeting notes and extract all action items.",
      created_at: "2026-04-07T16:32:00Z",
    },
    {
      id: "msg-022", role: "assistant",
      content: "Here's the summary of today's standup meeting with action items highlighted.\n\n**Key Updates:**\n- Engineering: Sprint velocity improved by 15%\n- Design: New component library ready for review\n- Product: Feature prioritization complete for Q2\n\n**Action Items:**\n1. @alice - Submit the API spec by Friday\n2. @bob - Review the design mockups for the dashboard\n3. @charlie - Schedule the security audit with the vendor",
      tokens_used: 650,
      cost_usd: 0.05,
      created_at: "2026-04-07T16:45:00Z",
    },
  ],
};

// ---------- Component ----------

export default function AgentChat() {
  const { conversationId } = useParams();

  const [conversations, setConversations] = useState<DemoConversation[]>(DEMO_CONVERSATIONS);
  const [selectedConvId, setSelectedConvId] = useState<string | null>(conversationId || null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Fetch agents
  const { data: agentsData } = useQuery({
    queryKey: ["agents-chat"],
    queryFn: () => agentsApi.list(),
  });
  const agents: DemoAgent[] = (agentsData as any)?.data?.items ?? (agentsData as any)?.data ?? DEMO_AGENTS;

  // Load messages when conversation selected
  useEffect(() => {
    if (selectedConvId) {
      // Try API first, fallback to demo
      chatApi.getMessages(selectedConvId).then((res: any) => {
        const items = res?.data?.items;
        if (items && items.length > 0) {
          setMessages(items);
        } else {
          setMessages(DEMO_MESSAGES[selectedConvId] ?? []);
        }
      }).catch(() => {
        setMessages(DEMO_MESSAGES[selectedConvId] ?? []);
      });
    } else {
      setMessages([]);
    }
  }, [selectedConvId]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
  }, []);

  const handleSend = async () => {
    if (!input.trim() || isLoading || !selectedConvId) return;

    const userMsg: ChatMsg = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: input.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    setIsLoading(true);

    try {
      const res = await chatApi.sendMessage(selectedConvId, userMsg.content);
      const assistantMsg = (res as any)?.data?.assistant_message;
      if (assistantMsg) {
        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        // Demo fallback
        const demoResponse: ChatMsg = {
          id: `msg-${Date.now() + 1}`,
          role: "assistant",
          content: "I've processed your request. This is a demo response since the backend is not connected. In production, this would be a real AI-generated response from the assigned agent.",
          tokens_used: 120,
          cost_usd: 0.003,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, demoResponse]);
      }
    } catch {
      const demoResponse: ChatMsg = {
        id: `msg-${Date.now() + 1}`,
        role: "assistant",
        content: "I've processed your request. This is a demo response since the backend is not connected. In production, this would be a real AI-generated response from the assigned agent.",
        tokens_used: 120,
        cost_usd: 0.003,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, demoResponse]);
    } finally {
      setIsLoading(false);
    }

    // Update conversation last message
    setConversations((prev) =>
      prev.map((c) =>
        c.id === selectedConvId
          ? { ...c, last_message: userMsg.content, last_message_at: userMsg.created_at }
          : c
      )
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    if (!selectedAgentId) {
      toast.error("Select an agent first");
      return;
    }
    const agent = agents.find((a) => a.id === selectedAgentId);
    const newConv: DemoConversation = {
      id: `conv-${Date.now()}`,
      title: "New Conversation",
      agent_id: selectedAgentId,
      agent_name: agent?.name ?? "Agent",
      last_message: "",
      last_message_at: new Date().toISOString(),
      total_cost_usd: 0,
    };
    setConversations((prev) => [newConv, ...prev]);
    setSelectedConvId(newConv.id);

    // Try to create via API
    chatApi.createConversation(selectedAgentId).catch(() => {});
  };

  const handleDeleteConversation = (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setConversations((prev) => prev.filter((c) => c.id !== convId));
    if (selectedConvId === convId) {
      setSelectedConvId(null);
      setMessages([]);
    }
    chatApi.deleteConversation(convId).catch(() => {});
    toast.success("Conversation deleted");
  };

  const toggleToolExpand = (msgId: string, toolIdx: number) => {
    const key = `${msgId}-${toolIdx}`;
    setExpandedTools((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const selectedConv = conversations.find((c) => c.id === selectedConvId);
  const selectedAgent = selectedConv ? agents.find((a) => a.id === selectedConv.agent_id) : null;

  const filteredConversations = conversations.filter(
    (c) =>
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.agent_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex h-[calc(100vh-theme(spacing.12)-theme(spacing.12))] lg:h-[calc(100vh-theme(spacing.12))] -m-6 bg-white dark:bg-neutral-900">
      {/* Left Sidebar */}
      <div className="w-72 border-r border-neutral-200 dark:border-neutral-700 flex flex-col shrink-0 bg-neutral-50 dark:bg-neutral-800/50">
        {/* Agent Selector */}
        <div className="p-3 border-b border-neutral-200 dark:border-neutral-700">
          <select
            className="w-full text-xs bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-600 rounded-lg px-3 py-2 text-neutral-700 dark:text-neutral-300 focus:ring-1 focus:ring-neutral-900 dark:focus:ring-neutral-400 focus:outline-none"
            value={selectedAgentId}
            onChange={(e) => setSelectedAgentId(e.target.value)}
          >
            <option value="">Select an agent...</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name} ({agent.status})
              </option>
            ))}
          </select>
        </div>

        {/* New Chat Button */}
        <div className="p-3 border-b border-neutral-200 dark:border-neutral-700">
          <button
            onClick={handleNewChat}
            className="w-full btn-primary flex items-center justify-center gap-2 text-xs py-2"
          >
            <Plus className="h-3.5 w-3.5" /> New Chat
          </button>
        </div>

        {/* Search */}
        <div className="px-3 pt-3 pb-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400 dark:text-neutral-500" />
            <input
              type="text"
              placeholder="Search conversations..."
              className="w-full text-xs bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-600 rounded-lg pl-8 pr-3 py-2 text-neutral-700 dark:text-neutral-300 placeholder:text-neutral-400 focus:ring-1 focus:ring-neutral-900 dark:focus:ring-neutral-400 focus:outline-none"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto px-2 pb-2">
          {filteredConversations.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="h-6 w-6 text-neutral-300 dark:text-neutral-600 mx-auto mb-2" />
              <p className="text-xs text-neutral-400 dark:text-neutral-500">No conversations</p>
            </div>
          ) : (
            filteredConversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => setSelectedConvId(conv.id)}
                className={cn(
                  "w-full text-left p-3 rounded-lg mb-1 transition-colors group",
                  selectedConvId === conv.id
                    ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
                    : "hover:bg-neutral-200 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300"
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold truncate flex-1">{conv.title}</span>
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => handleDeleteConversation(conv.id, e)}
                    className={cn(
                      "p-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer",
                      selectedConvId === conv.id
                        ? "hover:bg-neutral-700 dark:hover:bg-neutral-200"
                        : "hover:bg-neutral-300 dark:hover:bg-neutral-600"
                    )}
                  >
                    <Trash2 className="h-3 w-3" />
                  </span>
                </div>
                <p className={cn(
                  "text-[10px] mb-1",
                  selectedConvId === conv.id
                    ? "text-neutral-300 dark:text-neutral-600"
                    : "text-neutral-400 dark:text-neutral-500 dark:text-neutral-400 dark:text-neutral-500"
                )}>
                  {conv.agent_name}
                </p>
                <p className={cn(
                  "text-[11px] truncate",
                  selectedConvId === conv.id
                    ? "text-neutral-400 dark:text-neutral-500 dark:text-neutral-400 dark:text-neutral-500"
                    : "text-neutral-500 dark:text-neutral-400 dark:text-neutral-500"
                )}>
                  {conv.last_message || "No messages yet"}
                </p>
                <p className={cn(
                  "text-[10px] mt-1",
                  selectedConvId === conv.id
                    ? "text-neutral-400 dark:text-neutral-500 dark:text-neutral-400 dark:text-neutral-500"
                    : "text-neutral-400 dark:text-neutral-500"
                )}>
                  {conv.last_message_at ? formatDate(conv.last_message_at) : ""}
                </p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {selectedConv ? (
          <>
            {/* Chat Header */}
            <div className="h-14 flex items-center justify-between px-5 border-b border-neutral-200 dark:border-neutral-700 shrink-0 bg-white dark:bg-neutral-800">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-neutral-100 dark:bg-neutral-700 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                      {selectedConv.agent_name}
                    </span>
                    <div className={cn(
                      "w-2 h-2 rounded-full",
                      selectedAgent?.status === "idle" ? "bg-emerald-500" :
                      selectedAgent?.status === "busy" ? "bg-amber-500" :
                      "bg-neutral-300"
                    )} />
                    {selectedAgent?.llm_model && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">
                        {selectedAgent.llm_model}
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-neutral-400 dark:text-neutral-500">{selectedConv.title}</p>
                </div>
              </div>
              <div className="flex items-center gap-3 text-xs text-neutral-400 dark:text-neutral-500">
                <span className="flex items-center gap-1">
                  <DollarSign className="h-3 w-3" />
                  ${selectedConv.total_cost_usd.toFixed(3)}
                </span>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {messages.map((msg) => (
                <div key={msg.id}>
                  {msg.role === "system" ? (
                    <div className="flex justify-center">
                      <span className="text-[10px] text-neutral-400 bg-neutral-100 dark:bg-neutral-800 px-3 py-1 rounded-full">
                        {msg.content}
                      </span>
                    </div>
                  ) : msg.role === "user" ? (
                    <div className="flex justify-end">
                      <div className="max-w-[70%] flex gap-2.5 items-end">
                        <div>
                          <div className="bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 rounded-2xl rounded-br-md px-4 py-2.5">
                            <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                          </div>
                          <p className="text-[10px] text-neutral-400 text-right mt-1">
                            {formatDate(msg.created_at)}
                          </p>
                        </div>
                        <div className="w-7 h-7 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center shrink-0">
                          <User className="h-3.5 w-3.5 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex justify-start">
                      <div className="max-w-[75%] flex gap-2.5 items-start">
                        <div className="w-7 h-7 rounded-full bg-neutral-100 dark:bg-neutral-700 flex items-center justify-center shrink-0 mt-0.5">
                          <Bot className="h-3.5 w-3.5 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />
                        </div>
                        <div>
                          {/* Tool calls (before content) */}
                          {msg.tool_calls && msg.tool_calls.length > 0 && (
                            <div className="mb-2 space-y-1.5">
                              {msg.tool_calls.map((tool, idx) => {
                                const key = `${msg.id}-${idx}`;
                                const isExpanded = expandedTools.has(key);
                                return (
                                  <div key={idx} className="border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden">
                                    <button
                                      onClick={() => toggleToolExpand(msg.id, idx)}
                                      className="w-full flex items-center gap-2 px-3 py-2 text-xs bg-neutral-50 dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
                                    >
                                      <Wrench className="h-3 w-3 text-neutral-400 dark:text-neutral-500" />
                                      <span className="font-mono font-medium text-neutral-600 dark:text-neutral-400 dark:text-neutral-500">{tool.name}</span>
                                      {tool.status === "success" ? (
                                        <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                                      ) : tool.status === "error" ? (
                                        <XCircle className="h-3 w-3 text-red-500" />
                                      ) : (
                                        <Loader2 className="h-3 w-3 text-amber-500 animate-spin" />
                                      )}
                                      {tool.duration && (
                                        <span className="text-neutral-400 ml-auto">{tool.duration}</span>
                                      )}
                                      {isExpanded ? (
                                        <ChevronDown className="h-3 w-3 text-neutral-400 dark:text-neutral-500" />
                                      ) : (
                                        <ChevronRight className="h-3 w-3 text-neutral-400 dark:text-neutral-500" />
                                      )}
                                    </button>
                                    {isExpanded && (
                                      <div className="px-3 py-2 border-t border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 space-y-2">
                                        <div>
                                          <span className="text-[10px] font-medium text-neutral-400 uppercase">Input</span>
                                          <pre className="text-[11px] text-neutral-600 dark:text-neutral-400 font-mono mt-0.5 whitespace-pre-wrap break-all">
                                            {JSON.stringify(tool.args, null, 2)}
                                          </pre>
                                        </div>
                                        {tool.result && (
                                          <div>
                                            <span className="text-[10px] font-medium text-neutral-400 uppercase">Output</span>
                                            <pre className="text-[11px] text-neutral-600 dark:text-neutral-400 font-mono mt-0.5 whitespace-pre-wrap break-all">
                                              {tool.result}
                                            </pre>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          )}

                          {/* Message content */}
                          <div className="bg-neutral-100 dark:bg-neutral-800 rounded-2xl rounded-bl-md px-4 py-2.5">
                            <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 whitespace-pre-wrap">
                              {msg.content}
                            </p>
                          </div>
                          <div className="flex items-center gap-3 mt-1">
                            <p className="text-[10px] text-neutral-400 dark:text-neutral-500">{formatDate(msg.created_at)}</p>
                            {msg.tokens_used !== undefined && msg.tokens_used > 0 && (
                              <span className="text-[10px] text-neutral-400 dark:text-neutral-500">
                                {msg.tokens_used.toLocaleString()} tokens
                              </span>
                            )}
                            {msg.cost_usd !== undefined && msg.cost_usd > 0 && (
                              <span className="text-[10px] text-neutral-400 dark:text-neutral-500">
                                ${msg.cost_usd.toFixed(4)}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Typing indicator */}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="flex gap-2.5 items-start">
                    <div className="w-7 h-7 rounded-full bg-neutral-100 dark:bg-neutral-700 flex items-center justify-center shrink-0">
                      <Bot className="h-3.5 w-3.5 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />
                    </div>
                    <div className="bg-neutral-100 dark:bg-neutral-800 rounded-2xl rounded-bl-md px-4 py-3">
                      <div className="flex gap-1.5">
                        <div className="w-2 h-2 rounded-full bg-neutral-400 animate-bounce [animation-delay:0ms]" />
                        <div className="w-2 h-2 rounded-full bg-neutral-400 animate-bounce [animation-delay:150ms]" />
                        <div className="w-2 h-2 rounded-full bg-neutral-400 animate-bounce [animation-delay:300ms]" />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Bar */}
            <div className="px-5 py-3 border-t border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 shrink-0">
              <div className="flex items-end gap-2">
                <button
                  className="p-2 rounded-lg text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors shrink-0"
                  title="Attach file"
                >
                  <Paperclip className="h-4 w-4" />
                </button>
                <div className="flex-1 relative">
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Type a message... (Shift+Enter for newline)"
                    rows={1}
                    className="w-full resize-none bg-neutral-100 dark:bg-neutral-700 border border-neutral-200 dark:border-neutral-600 rounded-xl px-4 py-2.5 text-sm text-neutral-800 dark:text-neutral-200 placeholder:text-neutral-400 focus:ring-1 focus:ring-neutral-900 dark:focus:ring-neutral-400 focus:outline-none"
                    style={{ maxHeight: 120 }}
                  />
                  <span className="absolute right-3 bottom-2 text-[10px] text-neutral-400 dark:text-neutral-500">
                    {input.length > 0 ? `${input.length}/32000` : ""}
                  </span>
                </div>
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading || !selectedConvId}
                  className={cn(
                    "p-2.5 rounded-xl transition-colors shrink-0",
                    input.trim() && !isLoading
                      ? "bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 hover:bg-neutral-800 dark:hover:bg-neutral-200"
                      : "bg-neutral-200 dark:bg-neutral-700 text-neutral-400 cursor-not-allowed"
                  )}
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        ) : (
          /* Empty state */
          <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
            <div className="w-16 h-16 rounded-2xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center mb-4">
              <MessageSquare className="h-8 w-8 text-neutral-300 dark:text-neutral-600" />
            </div>
            <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">Agent Chat</h2>
            <p className="text-sm text-neutral-400 max-w-sm mb-6">
              Select a conversation from the sidebar or create a new chat to start talking with an AI agent.
            </p>
            <div className="flex items-center gap-3">
              <select
                className="text-xs bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-600 rounded-lg px-3 py-2 text-neutral-700 dark:text-neutral-300 focus:ring-1 focus:ring-neutral-900 dark:focus:ring-neutral-400 focus:outline-none"
                value={selectedAgentId}
                onChange={(e) => setSelectedAgentId(e.target.value)}
              >
                <option value="">Select an agent...</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
              <button
                onClick={handleNewChat}
                className="btn-primary flex items-center gap-2 text-xs"
                disabled={!selectedAgentId}
              >
                <Plus className="h-3.5 w-3.5" /> New Chat
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
