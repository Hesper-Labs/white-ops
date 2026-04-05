import { useState } from "react";
import { Bot, Rocket } from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "../lib/utils";

type Category = "all" | "finance" | "tech" | "operations" | "marketing";

interface Preset {
  id: string;
  name: string;
  role: string;
  description: string;
  llm: string;
  tools: string[];
  category: Category;
}

const PRESETS: Preset[] = [
  {
    id: "p1",
    name: "Financial Analyst",
    role: "Finance",
    description: "Analyzes financial statements, generates reports, and tracks KPIs. Capable of reading spreadsheets and producing executive summaries.",
    llm: "GPT-4o",
    tools: ["Spreadsheet Reader", "PDF Parser", "Chart Generator", "Email Sender"],
    category: "finance",
  },
  {
    id: "p2",
    name: "Research Specialist",
    role: "Research",
    description: "Conducts deep market research, competitor analysis, and trend monitoring. Aggregates data from multiple sources into structured reports.",
    llm: "Claude 3.5 Sonnet",
    tools: ["Web Search", "Document Analyzer", "Summary Writer", "Data Extractor"],
    category: "operations",
  },
  {
    id: "p3",
    name: "Content Writer",
    role: "Creative",
    description: "Creates blog posts, newsletters, social media copy, and marketing materials aligned with brand guidelines.",
    llm: "GPT-4o",
    tools: ["Style Guide Reader", "SEO Analyzer", "Image Selector", "Publishing API"],
    category: "marketing",
  },
  {
    id: "p4",
    name: "Executive Assistant",
    role: "Administrative",
    description: "Manages scheduling, email triage, meeting summaries, and task prioritization for executives and team leads.",
    llm: "Claude 3.5 Sonnet",
    tools: ["Email Client", "Calendar API", "Task Manager", "Contact Lookup"],
    category: "operations",
  },
  {
    id: "p5",
    name: "Software Developer",
    role: "Engineering",
    description: "Reviews pull requests, writes tests, generates documentation, and automates code quality checks across repositories.",
    llm: "GPT-4o",
    tools: ["GitHub API", "Code Linter", "Test Runner", "Doc Generator"],
    category: "tech",
  },
  {
    id: "p6",
    name: "HR Manager",
    role: "Human Resources",
    description: "Screens resumes, drafts job descriptions, manages onboarding workflows, and generates HR compliance reports.",
    llm: "Claude 3.5 Sonnet",
    tools: ["Resume Parser", "Template Engine", "Email Sender", "Form Builder"],
    category: "operations",
  },
  {
    id: "p7",
    name: "Marketing Analyst",
    role: "Marketing",
    description: "Tracks campaign performance, analyzes conversion funnels, and generates attribution reports with actionable recommendations.",
    llm: "GPT-4o",
    tools: ["Analytics API", "Dashboard Builder", "A/B Test Analyzer", "Report Writer"],
    category: "marketing",
  },
  {
    id: "p8",
    name: "Legal Assistant",
    role: "Legal",
    description: "Reviews contracts, flags compliance risks, summarizes legal documents, and tracks regulatory changes.",
    llm: "Claude 3.5 Sonnet",
    tools: ["Document Analyzer", "Clause Extractor", "Compliance Checker", "PDF Parser"],
    category: "operations",
  },
  {
    id: "p9",
    name: "Data Scientist",
    role: "Data",
    description: "Builds data pipelines, runs statistical analyses, creates visualizations, and trains lightweight ML models on structured datasets.",
    llm: "GPT-4o",
    tools: ["Python Executor", "SQL Runner", "Chart Generator", "Model Trainer"],
    category: "tech",
  },
  {
    id: "p10",
    name: "Sales Representative",
    role: "Sales",
    description: "Generates outreach sequences, qualifies leads, prepares proposal decks, and updates CRM records automatically.",
    llm: "Claude 3.5 Sonnet",
    tools: ["CRM API", "Email Sender", "Deck Builder", "Lead Scorer"],
    category: "marketing",
  },
  {
    id: "p11",
    name: "Project Manager",
    role: "Management",
    description: "Tracks milestones, generates status reports, identifies blockers, and coordinates cross-team dependencies.",
    llm: "GPT-4o",
    tools: ["Task Manager", "Gantt Builder", "Slack Notifier", "Report Writer"],
    category: "operations",
  },
  {
    id: "p12",
    name: "Customer Support",
    role: "Support",
    description: "Handles support tickets, drafts responses, escalates complex issues, and maintains the internal knowledge base.",
    llm: "Claude 3.5 Sonnet",
    tools: ["Ticket System", "Knowledge Search", "Email Sender", "Sentiment Analyzer"],
    category: "operations",
  },
];

const TABS: { key: Category; label: string }[] = [
  { key: "all", label: "All" },
  { key: "finance", label: "Finance" },
  { key: "tech", label: "Tech" },
  { key: "operations", label: "Operations" },
  { key: "marketing", label: "Marketing" },
];

export default function AgentPresets() {
  const [activeTab, setActiveTab] = useState<Category>("all");

  const filtered = activeTab === "all" ? PRESETS : PRESETS.filter((p) => p.category === activeTab);

  function handleDeploy(preset: Preset) {
    toast.success(`Agent created from preset: ${preset.name}`);
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-neutral-900">Agent Presets</h1>
          <p className="text-xs text-neutral-400 mt-0.5">{PRESETS.length} preset profiles available</p>
        </div>
      </div>

      {/* Category tabs */}
      <div className="flex items-center gap-1 mb-6 border-b border-neutral-200">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              "px-4 py-2 text-xs font-medium transition-colors border-b-2 -mb-px",
              activeTab === tab.key
                ? "border-neutral-900 text-neutral-900"
                : "border-transparent text-neutral-400 hover:text-neutral-600",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Preset grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((preset) => (
          <div key={preset.id} className="card p-5 flex flex-col">
            {/* Top */}
            <div className="flex items-start gap-3 mb-3">
              <div className="h-9 w-9 rounded-md bg-neutral-100 border border-neutral-200 flex items-center justify-center flex-shrink-0">
                <Bot className="h-4.5 w-4.5 text-neutral-500" />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-neutral-900">{preset.name}</h3>
                <p className="text-[11px] text-neutral-400 font-medium">{preset.role}</p>
              </div>
            </div>

            {/* Description */}
            <p className="text-xs text-neutral-500 leading-relaxed mb-4 flex-1">{preset.description}</p>

            {/* LLM */}
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">LLM</span>
              <span className="badge-blue">{preset.llm}</span>
            </div>

            {/* Tools */}
            <div className="flex flex-wrap gap-1.5 mb-4">
              {preset.tools.map((tool) => (
                <span key={tool} className="badge-gray">{tool}</span>
              ))}
            </div>

            {/* Deploy */}
            <button
              onClick={() => handleDeploy(preset)}
              className="btn-primary flex items-center justify-center gap-1.5 w-full"
            >
              <Rocket className="h-3.5 w-3.5" />
              Deploy Agent
            </button>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="card p-12 text-center">
          <Bot className="h-10 w-10 text-neutral-300 mx-auto mb-3" />
          <p className="text-sm font-medium text-neutral-600">No presets in this category</p>
          <p className="text-xs text-neutral-400 mt-1">Try selecting a different category tab.</p>
        </div>
      )}
    </div>
  );
}
