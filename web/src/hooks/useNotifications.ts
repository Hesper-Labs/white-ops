import { useEffect } from "react";
import toast from "react-hot-toast";
import { useQueryClient } from "@tanstack/react-query";
import { useWebSocket } from "./useWebSocket";

export function useNotifications() {
  const queryClient = useQueryClient();
  const { subscribe } = useWebSocket();

  useEffect(() => {
    const unsubscribers = [
      subscribe("task.completed", (data) => {
        toast.success(`Task completed: ${data.title || "Untitled"}`);
        queryClient.invalidateQueries({ queryKey: ["tasks"] });
        queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      }),

      subscribe("task.failed", (data) => {
        toast.error(`Task failed: ${data.title || "Untitled"}`);
        queryClient.invalidateQueries({ queryKey: ["tasks"] });
      }),

      subscribe("agent.status", (data) => {
        queryClient.invalidateQueries({ queryKey: ["agents"] });
        if (data.status === "error") {
          toast.error(`Agent error: ${data.name || "Unknown"}`);
        }
      }),

      subscribe("worker.offline", (data) => {
        toast.error(`Worker offline: ${data.name || "Unknown"}`);
        queryClient.invalidateQueries({ queryKey: ["workers"] });
      }),

      subscribe("worker.online", (data) => {
        toast(`Worker online: ${data.name || "Unknown"}`);
        queryClient.invalidateQueries({ queryKey: ["workers"] });
      }),

      subscribe("message.new", (data) => {
        toast(`New message: ${data.subject || "No subject"}`);
        queryClient.invalidateQueries({ queryKey: ["messages"] });
      }),

      subscribe("notification", (data) => {
        const level = data.level as string;
        const message = `${data.title}: ${data.message}`;
        if (level === "error") toast.error(message);
        else if (level === "warning") toast(message, { icon: "!" });
        else toast.success(message);
      }),

      subscribe("system.alert", (data) => {
        toast.error(`System Alert: ${data.message || "Check dashboard"}`);
      }),
    ];

    return () => unsubscribers.forEach((unsub) => unsub());
  }, [subscribe, queryClient]);
}
