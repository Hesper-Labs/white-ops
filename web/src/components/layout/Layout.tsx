import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Bot, ListTodo, GitBranch, MessageSquare,
  FolderOpen, Server, Settings, LogOut, Menu, X,
  BarChart3, BookOpen, Activity, Clock, FileStack,
  UserCog, ScrollText, Sparkles, DollarSign,
  Shield, Brain, Zap, Rocket, GitPullRequest, ShoppingBag,
  MessageCircle, Terminal, KeyRound, ShieldCheck, Bell,
  Webhook, MailWarning,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { cn } from "../../lib/utils";
import { ThemeToggle } from "../ui/ThemeToggle";

const navigation = [
  // MAIN
  { name: "Dashboard", href: "/", icon: LayoutDashboard, section: "main" },
  { name: "Agent Chat", href: "/chat", icon: MessageCircle, section: "main" },
  { name: "Agents", href: "/agents", icon: Bot, section: "main" },
  { name: "Tasks", href: "/tasks", icon: ListTodo, section: "main" },
  { name: "Workflows", href: "/workflows", icon: GitBranch, section: "main" },
  { name: "Messages", href: "/messages", icon: MessageSquare, section: "main" },
  { name: "Files", href: "/files", icon: FolderOpen, section: "main" },
  // INTELLIGENCE
  { name: "Knowledge Base", href: "/knowledge", icon: BookOpen, section: "intelligence" },
  { name: "Analytics", href: "/analytics", icon: BarChart3, section: "intelligence" },
  { name: "Cost Dashboard", href: "/costs", icon: DollarSign, section: "intelligence" },
  { name: "Activity Feed", href: "/activity", icon: Activity, section: "intelligence" },
  { name: "Marketplace", href: "/marketplace", icon: ShoppingBag, section: "intelligence" },
  // OPERATIONS
  { name: "Schedules", href: "/schedules", icon: Clock, section: "operations" },
  { name: "Templates", href: "/templates", icon: FileStack, section: "operations" },
  { name: "Agent Presets", href: "/presets", icon: Sparkles, section: "operations" },
  { name: "Agent Memory", href: "/agent-memory", icon: Brain, section: "operations" },
  { name: "Code Reviews", href: "/reviews", icon: GitPullRequest, section: "operations" },
  // DEVOPS
  { name: "Workers", href: "/workers", icon: Server, section: "devops" },
  { name: "SSH Connections", href: "/ssh-connections", icon: Terminal, section: "devops" },
  { name: "Triggers", href: "/triggers", icon: Webhook, section: "devops" },
  { name: "Approvals", href: "/approvals", icon: ShieldCheck, section: "devops" },
  // RESILIENCE
  { name: "Circuit Breakers", href: "/circuit-breakers", icon: Zap, section: "resilience" },
  { name: "Dead Letter Queue", href: "/dead-letter", icon: MailWarning, section: "resilience" },
  { name: "Notifications", href: "/notifications", icon: Bell, section: "resilience" },
  // SYSTEM
  { name: "Users", href: "/users", icon: UserCog, section: "system" },
  { name: "Security", href: "/security", icon: Shield, section: "system" },
  { name: "Secrets", href: "/secrets", icon: KeyRound, section: "system" },
  { name: "Audit Log", href: "/audit", icon: ScrollText, section: "system" },
  { name: "Settings", href: "/settings", icon: Settings, section: "system" },
  { name: "Setup Wizard", href: "/setup", icon: Rocket, section: "system" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const { user, logout } = useAuthStore();

  return (
    <div className="flex h-screen bg-neutral-50 dark:bg-neutral-900">
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/30 dark:bg-black/50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      <aside className={cn(
        "fixed inset-y-0 left-0 z-50 w-60 bg-white dark:bg-neutral-800 border-r border-neutral-200 dark:border-neutral-700 flex flex-col transform transition-transform lg:translate-x-0 lg:static",
        sidebarOpen ? "translate-x-0" : "-translate-x-full",
      )}>
        {/* Header */}
        <div className="h-12 flex items-center px-4 border-b border-neutral-200 dark:border-neutral-700 shrink-0">
          <img src="/logo.png" alt="" className="h-5 w-5 mr-2" />
          <span className="text-xs font-bold text-neutral-900 dark:text-neutral-100 tracking-tight">White-Ops</span>
          <div className="ml-auto flex items-center gap-1.5">
            <ThemeToggle />
            <button className="lg:hidden" onClick={() => setSidebarOpen(false)}>
              <X className="h-4 w-4 text-neutral-400" />
            </button>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-3 px-2.5">
          {["main", "intelligence", "operations", "devops", "resilience", "system"].map((section) => (
            <div key={section}>
              {section === "intelligence" && <div className="sidebar-section">Intelligence</div>}
              {section === "operations" && <div className="sidebar-section">Operations</div>}
              {section === "devops" && <div className="sidebar-section">DevOps</div>}
              {section === "resilience" && <div className="sidebar-section">Resilience</div>}
              {section === "system" && <div className="sidebar-section">System</div>}
              {navigation.filter((i) => i.section === section).map((item) => {
                const isActive = item.href === "/" ? location.pathname === "/" : location.pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={cn(
                      "flex items-center gap-2.5 px-3 py-[7px] rounded-md text-[13px] font-medium transition-colors mb-0.5",
                      isActive
                        ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
                        : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-700 dark:hover:text-neutral-100",
                    )}
                  >
                    <item.icon className="h-4 w-4 flex-shrink-0" />
                    {item.name}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* User */}
        <div className="px-3 py-3 border-t border-neutral-200 dark:border-neutral-700 shrink-0">
          <div className="flex items-center gap-2.5 px-2">
            <div className="h-7 w-7 rounded-md bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 flex items-center justify-center text-xs font-bold">
              {user?.full_name?.[0] ?? "A"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-neutral-900 dark:text-neutral-100 truncate">{user?.full_name}</p>
              <p className="text-[10px] text-neutral-400 uppercase tracking-wider">{user?.role}</p>
            </div>
            <button onClick={logout} className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300" title="Logout">
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-12 flex items-center gap-3 px-4 bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 lg:hidden shrink-0">
          <button onClick={() => setSidebarOpen(true)}><Menu className="h-5 w-5 text-neutral-600 dark:text-neutral-400" /></button>
          <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">White-Ops</span>
        </header>
        <main className="flex-1 overflow-auto p-6 text-neutral-900 dark:text-neutral-100">{children}</main>
      </div>
    </div>
  );
}
