import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./stores/authStore";
import { useNotifications } from "./hooks/useNotifications";
import { ErrorBoundary } from "./components/ui/ErrorBoundary";
import { DemoBanner } from "./components/ui/DemoBanner";
import Layout from "./components/layout/Layout";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import Dashboard from "./pages/Dashboard";
import Agents from "./pages/Agents";
import Tasks from "./pages/Tasks";
import Workflows from "./pages/Workflows";
import Messages from "./pages/Messages";
import Files from "./pages/Files";
import Workers from "./pages/Workers";
import Analytics from "./pages/Analytics";
import Knowledge from "./pages/Knowledge";
import Collaboration from "./pages/Collaboration";
import Settings from "./pages/Settings";
import AuditLog from "./pages/AuditLog";
import UserManagement from "./pages/UserManagement";
import ActivityFeed from "./pages/ActivityFeed";
import ScheduledTasks from "./pages/ScheduledTasks";
import TaskTemplates from "./pages/TaskTemplates";
import AgentDetail from "./pages/AgentDetail";
import AgentPresets from "./pages/AgentPresets";
import TaskDetail from "./pages/TaskDetail";
import WorkflowBuilder from "./pages/WorkflowBuilder";
import CostDashboard from "./pages/CostDashboard";
import DeadLetterQueue from "./pages/DeadLetterQueue";
import SecuritySettings from "./pages/SecuritySettings";
import AgentMemory from "./pages/AgentMemory";
import CircuitBreakers from "./pages/CircuitBreakers";
import CodeReview from "./pages/CodeReview";
import SetupWizard from "./pages/SetupWizard";
import Marketplace from "./pages/Marketplace";
import AgentChat from "./pages/AgentChat";
import LiveTerminal from "./pages/LiveTerminal";
import SSHConnections from "./pages/SSHConnections";
import Secrets from "./pages/Secrets";
import Approvals from "./pages/Approvals";
import Triggers from "./pages/Triggers";
import NotificationCenter from "./pages/NotificationCenter";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, isLoading } = useAuthStore();
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-6 h-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin" />
      </div>
    );
  }
  if (!token) return <Navigate to="/login" />;
  return <>{children}</>;
}

function NotificationProvider({ children }: { children: React.ReactNode }) {
  useNotifications();
  return <>{children}</>;
}

export default function App() {
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/setup" element={<SetupWizard />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <NotificationProvider>
                <DemoBanner />
                <Layout>
                  <ErrorBoundary>
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/agents" element={<Agents />} />
                      <Route path="/agents/:agentId" element={<AgentDetail />} />
                      <Route path="/tasks" element={<Tasks />} />
                      <Route path="/tasks/:taskId" element={<TaskDetail />} />
                      <Route path="/workflows" element={<Workflows />} />
                      <Route path="/workflows/builder" element={<WorkflowBuilder />} />
                      <Route path="/presets" element={<AgentPresets />} />
                      <Route path="/messages" element={<Messages />} />
                      <Route path="/files" element={<Files />} />
                      <Route path="/collaboration" element={<Collaboration />} />
                      <Route path="/knowledge" element={<Knowledge />} />
                      <Route path="/analytics" element={<Analytics />} />
                      <Route path="/activity" element={<ActivityFeed />} />
                      <Route path="/schedules" element={<ScheduledTasks />} />
                      <Route path="/templates" element={<TaskTemplates />} />
                      <Route path="/workers" element={<Workers />} />
                      <Route path="/users" element={<UserManagement />} />
                      <Route path="/audit" element={<AuditLog />} />
                      <Route path="/costs" element={<CostDashboard />} />
                      <Route path="/dead-letter" element={<DeadLetterQueue />} />
                      <Route path="/security" element={<SecuritySettings />} />
                      <Route path="/agent-memory" element={<AgentMemory />} />
                      <Route path="/circuit-breakers" element={<CircuitBreakers />} />
                      <Route path="/reviews" element={<CodeReview />} />
                      <Route path="/marketplace" element={<Marketplace />} />
                      <Route path="/chat" element={<AgentChat />} />
                      <Route path="/chat/:agentId" element={<AgentChat />} />
                      <Route path="/terminal/:agentId" element={<LiveTerminal />} />
                      <Route path="/ssh-connections" element={<SSHConnections />} />
                      <Route path="/secrets" element={<Secrets />} />
                      <Route path="/approvals" element={<Approvals />} />
                      <Route path="/triggers" element={<Triggers />} />
                      <Route path="/notifications" element={<NotificationCenter />} />
                      <Route path="/settings" element={<Settings />} />
                      <Route path="*" element={<NotFound />} />
                    </Routes>
                  </ErrorBoundary>
                </Layout>
              </NotificationProvider>
            </ProtectedRoute>
          }
        />
      </Routes>
    </ErrorBoundary>
  );
}
