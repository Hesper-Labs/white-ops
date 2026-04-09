import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search, Star, Download, ChevronLeft, ChevronRight, ShoppingBag,
  Filter, TrendingUp, ArrowUpDown,
  Code2, BarChart3, Wrench, FileText, Shield, Users, Banknote,
  ClipboardList, Cloud, Headphones, TestTube2, Mail, Database, Scale, Share2,
} from "lucide-react";
import { marketplaceApi } from "../api/endpoints";
import toast from "react-hot-toast";

const ICON_MAP: Record<string, React.ElementType> = {
  code: Code2, "bar-chart": BarChart3, wrench: Wrench, "file-text": FileText,
  shield: Shield, users: Users, banknote: Banknote, search: Search,
  clipboard: ClipboardList, cloud: Cloud, headphones: Headphones,
  "test-tube": TestTube2, mail: Mail, database: Database, scale: Scale, "share-2": Share2,
};

interface Template {
  id: string;
  name: string;
  category: string;
  description: string;
  author: string;
  rating: number;
  downloads: number;
  tags: string[];
  icon: string;
  featured?: boolean;
  tools: string[];
}

const TEMPLATES: Template[] = [
  { id: "1", name: "Full-Stack Developer", category: "development", description: "Expert at writing, reviewing, and debugging code across React, Python, and Node.js. Integrates with GitHub for PR management.", author: "White-Ops Team", rating: 4.8, downloads: 12500, tags: ["code", "github", "testing"], icon: "code", featured: true, tools: ["claude_code", "git_ops", "shell", "docker_ops", "github_integration"] },
  { id: "2", name: "Data Analyst Pro", category: "data", description: "Analyzes datasets, creates visualizations, generates reports. Handles Excel, CSV, databases, and statistical analysis.", author: "White-Ops Team", rating: 4.7, downloads: 9800, tags: ["data", "excel", "charts"], icon: "bar-chart", featured: true, tools: ["excel", "analysis", "visualization", "database", "reporter"] },
  { id: "3", name: "DevOps Engineer", category: "devops", description: "Manages infrastructure, CI/CD pipelines, Kubernetes clusters, and monitoring. Terraform, Ansible, and cloud provider support.", author: "White-Ops Team", rating: 4.6, downloads: 7200, tags: ["k8s", "terraform", "ci-cd"], icon: "wrench", featured: true, tools: ["terraform", "kubernetes", "ci_cd", "docker_ops", "shell"] },
  { id: "4", name: "Content Writer", category: "communication", description: "Creates professional documents, emails, presentations, and reports. SEO-optimized content and multi-language support.", author: "White-Ops Team", rating: 4.5, downloads: 6500, tags: ["writing", "email", "docs"], icon: "file-text", tools: ["word", "powerpoint", "pdf", "email_ext", "translator"] },
  { id: "5", name: "Security Auditor", category: "devops", description: "Scans for vulnerabilities, checks dependencies, audits code for security issues. OWASP compliance checking.", author: "White-Ops Team", rating: 4.9, downloads: 5400, tags: ["security", "audit", "compliance"], icon: "shield", featured: true, tools: ["vuln_scanner", "secret_scanner", "code_review", "shell"] },
  { id: "6", name: "HR Assistant", category: "hr", description: "Manages employee records, leave requests, payroll calculations, and onboarding checklists.", author: "Community", rating: 4.3, downloads: 3200, tags: ["hr", "payroll", "leave"], icon: "users", tools: ["employee_directory", "leave_manager", "payroll", "email_ext"] },
  { id: "7", name: "Financial Analyst", category: "finance", description: "Handles bookkeeping, invoice generation, expense reports, currency conversion, and tax calculations.", author: "Community", rating: 4.4, downloads: 4100, tags: ["finance", "invoice", "tax"], icon: "banknote", tools: ["bookkeeping", "invoice", "currency", "excel", "pdf"] },
  { id: "8", name: "Research Specialist", category: "research", description: "Conducts web research, scrapes data, summarizes articles, and compiles research reports with citations.", author: "White-Ops Team", rating: 4.6, downloads: 8900, tags: ["research", "web", "summarize"], icon: "search", tools: ["browser", "search", "web_scraper", "text_summarizer", "pdf"] },
  { id: "9", name: "Project Manager", category: "hr", description: "Tracks projects, milestones, and tasks. Generates status reports and manages team timelines.", author: "Community", rating: 4.2, downloads: 2800, tags: ["project", "tracking", "reports"], icon: "clipboard", tools: ["project_tracker", "time_tracker", "excel", "email_ext", "slack"] },
  { id: "10", name: "Cloud Architect", category: "devops", description: "Manages AWS, Azure, and GCP resources. Infrastructure provisioning, monitoring, and cost optimization.", author: "White-Ops Team", rating: 4.7, downloads: 6100, tags: ["aws", "azure", "gcp"], icon: "cloud", tools: ["aws", "azure_cloud", "gcp_cloud", "terraform", "prometheus"] },
  { id: "11", name: "Customer Support Bot", category: "communication", description: "Handles customer inquiries, creates tickets, searches knowledge bases, and drafts responses.", author: "Community", rating: 4.1, downloads: 3600, tags: ["support", "tickets", "knowledge"], icon: "headphones", tools: ["email_ext", "slack", "search", "text_summarizer"] },
  { id: "12", name: "QA Tester", category: "development", description: "Generates test cases, runs automated tests, reports bugs, and tracks test coverage.", author: "Community", rating: 4.3, downloads: 4300, tags: ["testing", "qa", "bugs"], icon: "test-tube", tools: ["claude_code", "shell", "browser", "git_ops"] },
  { id: "13", name: "Email Campaign Manager", category: "communication", description: "Designs email campaigns, manages mailing lists, tracks open rates, and A/B tests subject lines.", author: "Community", rating: 4.0, downloads: 2100, tags: ["email", "marketing", "campaigns"], icon: "mail", tools: ["email_ext", "excel", "pdf", "text_summarizer"] },
  { id: "14", name: "Database Administrator", category: "development", description: "Manages PostgreSQL and MySQL databases, runs migrations, optimizes queries, and handles backups.", author: "White-Ops Team", rating: 4.5, downloads: 3800, tags: ["database", "sql", "backup"], icon: "database", tools: ["database", "shell", "backup", "monitoring"] },
  { id: "15", name: "Legal Document Reviewer", category: "research", description: "Reviews contracts, NDAs, and compliance documents. Highlights risks and suggests amendments.", author: "Community", rating: 4.2, downloads: 1900, tags: ["legal", "contracts", "compliance"], icon: "scale", tools: ["pdf", "word", "text_summarizer", "search"] },
  { id: "16", name: "Social Media Manager", category: "communication", description: "Schedules posts, monitors engagement, generates content calendars, and analyzes social metrics.", author: "Community", rating: 4.1, downloads: 2400, tags: ["social", "marketing", "content"], icon: "share-2", tools: ["browser", "excel", "image", "text_summarizer"] },
];

const CATEGORIES = [
  { id: "all", label: "All" },
  { id: "development", label: "Development" },
  { id: "data", label: "Data Analysis" },
  { id: "hr", label: "HR & Admin" },
  { id: "finance", label: "Finance" },
  { id: "devops", label: "DevOps" },
  { id: "communication", label: "Communication" },
  { id: "research", label: "Research" },
];

type SortKey = "rating" | "downloads" | "name";

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          className={`h-3.5 w-3.5 ${
            star <= Math.round(rating)
              ? "fill-neutral-400 text-neutral-400 dark:fill-neutral-500 dark:text-neutral-500 dark:text-neutral-400 dark:text-neutral-500"
              : "text-neutral-300 dark:text-neutral-600"
          }`}
        />
      ))}
      <span className="text-xs text-neutral-500 dark:text-neutral-400 ml-1">{rating.toFixed(1)}</span>
    </div>
  );
}

function FeaturedCarousel({ templates, onInstall }: { templates: Template[]; onInstall: (t: Template) => void }) {
  const [offset, setOffset] = useState(0);
  const visible = 4;
  const maxOffset = Math.max(0, templates.length - visible);

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />
          <h2 className="text-lg font-semibold">Featured Templates</h2>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setOffset(Math.max(0, offset - 1))}
            disabled={offset === 0}
            className="p-1.5 rounded-md border border-neutral-200 dark:border-neutral-700 disabled:opacity-30 hover:bg-neutral-100 dark:hover:bg-neutral-700"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            onClick={() => setOffset(Math.min(maxOffset, offset + 1))}
            disabled={offset >= maxOffset}
            className="p-1.5 rounded-md border border-neutral-200 dark:border-neutral-700 disabled:opacity-30 hover:bg-neutral-100 dark:hover:bg-neutral-700"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {templates.slice(offset, offset + visible).map((t) => (
          <div
            key={t.id}
            className="relative overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 p-5"
          >
            <div className="absolute top-2 right-2">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-neutral-900 text-white dark:bg-white dark:text-neutral-900">
                FEATURED
              </span>
            </div>
            <div className="mb-3">{(() => { const IconComp = ICON_MAP[t.icon] || FileText; return <IconComp className="h-6 w-6 text-neutral-600 dark:text-neutral-400 dark:text-neutral-500" />; })()}</div>
            <h3 className="font-semibold text-sm mb-1">{t.name}</h3>
            <p className="text-xs text-neutral-600 dark:text-neutral-400 line-clamp-2 mb-3">{t.description}</p>
            <StarRating rating={t.rating} />
            <div className="flex items-center justify-between mt-3">
              <span className="text-xs text-neutral-500 dark:text-neutral-400 flex items-center gap-1">
                <Download className="h-3 w-3" />
                {t.downloads.toLocaleString()}
              </span>
              <button
                onClick={() => onInstall(t)}
                className="text-xs font-medium px-3 py-1.5 rounded-md bg-neutral-900 text-white hover:bg-neutral-800 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200 transition-colors"
              >
                Install
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Marketplace() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [sortBy, setSortBy] = useState<SortKey>("downloads");

  const featured = TEMPLATES.filter((t) => t.featured);

  const filtered = useMemo(() => {
    let results = TEMPLATES;
    if (category !== "all") {
      results = results.filter((t) => t.category === category);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      results = results.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q) ||
          t.tags.some((tag) => tag.toLowerCase().includes(q)),
      );
    }
    results = [...results].sort((a, b) => {
      if (sortBy === "rating") return b.rating - a.rating;
      if (sortBy === "downloads") return b.downloads - a.downloads;
      return a.name.localeCompare(b.name);
    });
    return results;
  }, [search, category, sortBy]);

  const handleInstall = (template: Template) => {
    marketplaceApi.installTemplate(template.id).catch(() => {});
    toast.success(`Template installed! Agent "${template.name}" created.`);
    setTimeout(() => navigate("/agents"), 1200);
  };

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <ShoppingBag className="h-6 w-6 text-neutral-700 dark:text-neutral-300" />
          <div>
            <h1 className="text-2xl font-bold">Marketplace</h1>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">Browse and install pre-built agent templates</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400 dark:text-neutral-500" />
            <input
              type="text"
              placeholder="Search templates..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-9 w-64"
            />
          </div>
          <div className="relative">
            <ArrowUpDown className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400 dark:text-neutral-500" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortKey)}
              className="input pl-9 pr-8 appearance-none"
            >
              <option value="downloads">Most Popular</option>
              <option value="rating">Highest Rated</option>
              <option value="name">Name A-Z</option>
            </select>
          </div>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="border-b border-neutral-200 dark:border-neutral-700 mb-6">
        <nav className="flex gap-0 -mb-px overflow-x-auto" role="tablist">
          {CATEGORIES.map((cat) => {
            const isActive = category === cat.id;
            const count = cat.id === "all" ? TEMPLATES.length : TEMPLATES.filter((t) => t.category === cat.id).length;
            return (
              <button
                key={cat.id}
                role="tab"
                aria-selected={isActive}
                onClick={() => setCategory(cat.id)}
                className={`inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  isActive
                    ? "border-neutral-900 text-neutral-900 dark:border-white dark:text-white"
                    : "border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300 dark:text-neutral-400 dark:hover:text-neutral-300"
                }`}
              >
                {cat.label}
                <span
                  className={`inline-flex items-center justify-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                    isActive
                      ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
                      : "bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300"
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Featured Section */}
      {category === "all" && !search && <FeaturedCarousel templates={featured} onInstall={handleInstall} />}

      {/* Template Grid */}
      {filtered.length === 0 ? (
        <div className="text-center py-16">
          <Filter className="h-10 w-10 text-neutral-300 dark:text-neutral-600 mx-auto mb-3" />
          <p className="text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">No templates found matching your criteria.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((t) => (
            <div
              key={t.id}
              className="card p-5 hover:shadow-md transition-shadow flex flex-col"
            >
              <div className="flex items-start gap-3 mb-3">
                <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-lg bg-neutral-100 dark:bg-neutral-700">
                  {(() => { const IconComp = ICON_MAP[t.icon] || FileText; return <IconComp className="h-5 w-5 text-neutral-600 dark:text-neutral-400 dark:text-neutral-500" />; })()}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-sm truncate">{t.name}</h3>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{t.author}</p>
                </div>
              </div>
              <p className="text-xs text-neutral-600 dark:text-neutral-400 line-clamp-2 mb-3 flex-1">
                {t.description}
              </p>
              <div className="flex flex-wrap gap-1.5 mb-3">
                {t.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300"
                  >
                    {tag}
                  </span>
                ))}
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-neutral-100 dark:border-neutral-700">
                <div className="flex items-center gap-3">
                  <StarRating rating={t.rating} />
                  <span className="text-xs text-neutral-400 flex items-center gap-1">
                    <Download className="h-3 w-3" />
                    {t.downloads.toLocaleString()}
                  </span>
                </div>
                <button
                  onClick={() => handleInstall(t)}
                  className="text-xs font-medium px-3 py-1.5 rounded-md bg-neutral-900 text-white hover:bg-neutral-800 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200 transition-colors"
                >
                  Install
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
