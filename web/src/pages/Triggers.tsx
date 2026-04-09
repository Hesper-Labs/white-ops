import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Zap, Plus, Clock, CheckCircle2,
  XCircle,
} from "lucide-react";
import { triggersApi } from "../api/endpoints";
import { cn, formatDate } from "../lib/utils";
import toast from "react-hot-toast";

const DEMO_TRIGGERS = [
  {
    id: "trg1", name: "Daily Report Generation", type: "cron",
    schedule: "0 9 * * 1-5", enabled: true, agent_name: "Report Agent",
    last_run: "2026-04-08T09:00:00Z", next_run: "2026-04-09T09:00:00Z",
    run_count: 85, last_status: "success",
  },
  {
    id: "trg2", name: "Webhook: New PR", type: "webhook",
    schedule: null, enabled: true, agent_name: "Code Review Agent",
    last_run: "2026-04-08T11:20:00Z", next_run: null,
    run_count: 234, last_status: "success",
  },
  {
    id: "trg3", name: "Hourly Health Check", type: "cron",
    schedule: "0 * * * *", enabled: false, agent_name: "Monitoring Agent",
    last_run: "2026-04-07T15:00:00Z", next_run: null,
    run_count: 1420, last_status: "failed",
  },
];

export default function Triggers() {
  const [showForm, setShowForm] = useState(false);
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["triggers"],
    queryFn: () => triggersApi.getAll().then((r) => r.data),
    placeholderData: DEMO_TRIGGERS,
  });

  const triggers = data ?? DEMO_TRIGGERS;

  const toggleMutation = useMutation({
    mutationFn: ({ id }: { id: string; enabled: boolean }) =>
      triggersApi.toggle(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["triggers"] });
      toast.success("Trigger updated");
    },
    onError: () => toast.error("Failed to update trigger"),
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Triggers</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
            Automate agent execution with cron schedules and webhooks
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 rounded-lg hover:opacity-90"
        >
          <Plus className="h-4 w-4" /> New Trigger
        </button>
      </div>

      <div className="grid gap-4">
        {triggers.map((trigger: Record<string, any>) => (
          <div
            key={trigger.id as string}
            className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg p-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={cn(
                  "h-9 w-9 rounded-lg flex items-center justify-center",
                  trigger.enabled ? "bg-violet-50 dark:bg-violet-900/30" : "bg-neutral-100 dark:bg-neutral-700",
                )}>
                  <Zap className={cn(
                    "h-4 w-4",
                    trigger.enabled ? "text-violet-600 dark:text-violet-400" : "text-neutral-400 dark:text-neutral-500",
                  )} />
                </div>
                <div>
                  <p className="text-sm font-semibold">{trigger.name as string}</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">
                    {trigger.agent_name as string}
                    {trigger.schedule && <> &middot; <Clock className="h-3 w-3 inline" /> {trigger.schedule as string}</>}
                    {trigger.type === "webhook" && <> &middot; Webhook</>}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-neutral-400 dark:text-neutral-500">{trigger.run_count as number} runs</span>
                {trigger.last_status === "success" ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                ) : trigger.last_status === "failed" ? (
                  <XCircle className="h-4 w-4 text-red-500" />
                ) : null}
                <button
                  onClick={() => toggleMutation.mutate({
                    id: trigger.id as string,
                    enabled: !(trigger.enabled as boolean),
                  })}
                  className={cn(
                    "relative h-5 w-9 rounded-full transition-colors",
                    trigger.enabled ? "bg-emerald-500" : "bg-neutral-300 dark:bg-neutral-600",
                  )}
                >
                  <span className={cn(
                    "absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform",
                    trigger.enabled ? "left-[18px]" : "left-0.5",
                  )} />
                </button>
              </div>
            </div>
            <div className="flex gap-4 mt-2 text-[11px] text-neutral-400 dark:text-neutral-500">
              {trigger.last_run && <span>Last: {formatDate(trigger.last_run as string)}</span>}
              {trigger.next_run && <span>Next: {formatDate(trigger.next_run as string)}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
