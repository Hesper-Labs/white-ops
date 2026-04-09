import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  KeyRound, Plus, Trash2, Shield,
} from "lucide-react";
import api from "../api/client";
import { formatDate } from "../lib/utils";
import toast from "react-hot-toast";

const DEMO_SECRETS = [
  {
    id: "sec1", key: "OPENAI_API_KEY", description: "OpenAI API key for GPT models",
    created_at: "2026-01-10T08:00:00Z", updated_at: "2026-03-15T12:00:00Z",
    accessed_count: 342, last_accessed: "2026-04-08T10:00:00Z",
  },
  {
    id: "sec2", key: "ANTHROPIC_API_KEY", description: "Claude API access",
    created_at: "2026-01-10T08:00:00Z", updated_at: "2026-04-01T09:00:00Z",
    accessed_count: 1205, last_accessed: "2026-04-08T11:30:00Z",
  },
  {
    id: "sec3", key: "SLACK_WEBHOOK_URL", description: "Slack notification webhook",
    created_at: "2026-02-05T14:00:00Z", updated_at: "2026-02-05T14:00:00Z",
    accessed_count: 89, last_accessed: "2026-04-07T18:00:00Z",
  },
  {
    id: "sec4", key: "AWS_ACCESS_KEY_ID", description: "AWS IAM credentials",
    created_at: "2026-03-01T10:00:00Z", updated_at: "2026-03-01T10:00:00Z",
    accessed_count: 56, last_accessed: "2026-04-06T14:00:00Z",
  },
];

export default function Secrets() {
  const [showForm, setShowForm] = useState(false);
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["secrets"],
    queryFn: () => api.get("/secrets/").then((r) => r.data),
    placeholderData: DEMO_SECRETS,
  });

  const secrets = data ?? DEMO_SECRETS;

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/secrets/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["secrets"] });
      toast.success("Secret deleted");
    },
    onError: () => toast.error("Failed to delete secret"),
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Secrets Vault</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
            Encrypted storage for API keys, tokens, and credentials
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 rounded-lg hover:opacity-90"
        >
          <Plus className="h-4 w-4" /> Add Secret
        </button>
      </div>

      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 flex items-start gap-2">
        <Shield className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
        <p className="text-xs text-amber-700 dark:text-amber-300">
          All secrets are encrypted at rest with AES-256. Access is audit-logged.
        </p>
      </div>

      <div className="grid gap-3">
        {secrets.map((secret: Record<string, unknown>) => (
          <div
            key={secret.id as string}
            className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg p-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-violet-50 dark:bg-violet-900/30 flex items-center justify-center">
                  <KeyRound className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                </div>
                <div>
                  <p className="text-sm font-mono font-semibold">{secret.key as string}</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">{secret.description as string}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-neutral-400 dark:text-neutral-500">
                  {secret.accessed_count as number} accesses
                </span>
                <button
                  onClick={() => deleteMutation.mutate(secret.id as string)}
                  className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-neutral-400 hover:text-red-600"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
            <p className="text-[11px] text-neutral-400 mt-2">
              Updated: {formatDate(secret.updated_at as string)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
