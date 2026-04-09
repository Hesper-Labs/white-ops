import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Terminal, Plus, Trash2,
  Key,
} from "lucide-react";
import api from "../api/client";
import { cn, formatDate } from "../lib/utils";
import toast from "react-hot-toast";

const DEMO_CONNECTIONS = [
  {
    id: "ssh1", name: "Production Server", host: "prod-01.example.com", port: 22,
    username: "deploy", auth_type: "key", status: "connected",
    last_used: "2026-04-08T10:30:00Z", created_at: "2026-01-15T08:00:00Z",
  },
  {
    id: "ssh2", name: "Staging Server", host: "staging.example.com", port: 22,
    username: "admin", auth_type: "key", status: "disconnected",
    last_used: "2026-04-07T16:45:00Z", created_at: "2026-02-20T14:00:00Z",
  },
  {
    id: "ssh3", name: "Dev Database", host: "db-dev.internal", port: 2222,
    username: "dbadmin", auth_type: "password", status: "connected",
    last_used: "2026-04-08T09:15:00Z", created_at: "2026-03-01T10:00:00Z",
  },
];

export default function SSHConnections() {
  const [showForm, setShowForm] = useState(false);
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["ssh-connections"],
    queryFn: () => api.get("/ssh-connections/").then((r) => r.data),
    placeholderData: DEMO_CONNECTIONS,
  });

  const connections = data ?? DEMO_CONNECTIONS;

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/ssh-connections/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ssh-connections"] });
      toast.success("Connection removed");
    },
    onError: () => toast.error("Failed to remove connection"),
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">SSH Connections</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
            Manage SSH connections for remote agent execution
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 rounded-lg hover:opacity-90"
        >
          <Plus className="h-4 w-4" /> Add Connection
        </button>
      </div>

      <div className="grid gap-4">
        {connections.map((conn: Record<string, string>) => (
          <div
            key={conn.id as string}
            className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg p-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={cn(
                  "h-9 w-9 rounded-lg flex items-center justify-center",
                  conn.status === "connected"
                    ? "bg-emerald-50 dark:bg-emerald-900/30"
                    : "bg-neutral-100 dark:bg-neutral-700",
                )}>
                  <Terminal className={cn(
                    "h-4 w-4",
                    conn.status === "connected" ? "text-emerald-600 dark:text-emerald-400" : "text-neutral-400 dark:text-neutral-500",
                  )} />
                </div>
                <div>
                  <p className="text-sm font-semibold">{conn.name as string}</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">
                    {conn.username}@{conn.host}:{conn.port}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn(
                  "text-xs font-medium px-2 py-1 rounded-full",
                  conn.status === "connected"
                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                    : "bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400 dark:text-neutral-500",
                )}>
                  {conn.status as string}
                </span>
                <span className="text-xs text-neutral-400 dark:text-neutral-500">
                  <Key className="h-3 w-3 inline mr-1" />
                  {conn.auth_type as string}
                </span>
                <button
                  onClick={() => deleteMutation.mutate(conn.id as string)}
                  className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-neutral-400 hover:text-red-600"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
            {conn.last_used && (
              <p className="text-[11px] text-neutral-400 mt-2">
                Last used: {formatDate(conn.last_used as string)}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
