import { useQuery } from "@tanstack/react-query";
import { MessageSquare } from "lucide-react";
import { messagesApi } from "../api/endpoints";
import { formatDate } from "../lib/utils";

export default function Messages() {
  const { data, isLoading } = useQuery({
    queryKey: ["messages"],
    queryFn: () => messagesApi.list(),
    refetchInterval: 5000,
  });

  const messages = data?.data ?? [];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Messages</h1>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      ) : messages.length === 0 ? (
        <div className="card p-12 text-center">
          <MessageSquare className="h-12 w-12 text-surface-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-surface-700">No messages yet</h3>
          <p className="text-surface-400 mt-1">Agent-to-agent messages will appear here.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {messages.map((msg: any) => (
            <div key={msg.id as string} className={`card p-4 ${!(msg.is_read as boolean) ? "border-l-4 border-l-primary-500" : ""}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="badge-blue">{msg.channel as string}</span>
                  {msg.subject && <span className="font-medium text-sm">{msg.subject as string}</span>}
                </div>
                <span className="text-xs text-surface-400">{formatDate(msg.created_at as string)}</span>
              </div>
              <p className="text-sm text-surface-600">{msg.body as string}</p>
              <div className="flex gap-4 mt-2 text-xs text-surface-400">
                <span>From: {(msg.sender_agent_id as string).slice(0, 8)}...</span>
                <span>To: {(msg.recipient_agent_id as string).slice(0, 8)}...</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
