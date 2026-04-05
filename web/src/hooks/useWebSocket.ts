import { useEffect, useRef, useCallback } from "react";

type EventHandler = (data: Record<string, unknown>) => void;

interface UseWebSocketOptions {
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export function useWebSocket(options?: UseWebSocketOptions) {
  const ws = useRef<WebSocket | null>(null);
  const handlers = useRef<Map<string, Set<EventHandler>>>(new Map());
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const reconnectDelay = useRef(1000);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws`;

    const socket = new WebSocket(url);

    socket.onopen = () => {
      reconnectDelay.current = 1000;
      options?.onConnect?.();

      // Keepalive ping
      const pingInterval = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);

      socket.addEventListener("close", () => clearInterval(pingInterval));
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        const eventHandlers = handlers.current.get(message.type);
        if (eventHandlers) {
          eventHandlers.forEach((handler) => handler(message.data));
        }
        // Also notify wildcard listeners
        const wildcardHandlers = handlers.current.get("*");
        if (wildcardHandlers) {
          wildcardHandlers.forEach((handler) =>
            handler({ type: message.type, ...message.data }),
          );
        }
      } catch {
        // Ignore parse errors
      }
    };

    socket.onclose = () => {
      options?.onDisconnect?.();
      reconnectTimer.current = setTimeout(() => {
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000);
        connect();
      }, reconnectDelay.current);
    };

    socket.onerror = () => socket.close();

    ws.current = socket;
  }, [options]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      ws.current?.close();
    };
  }, [connect]);

  const subscribe = useCallback(
    (event: string, handler: EventHandler): (() => void) => {
      if (!handlers.current.has(event)) {
        handlers.current.set(event, new Set());
      }
      handlers.current.get(event)!.add(handler);

      // Tell server we want this event
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: "subscribe", event }));
      }

      return () => {
        handlers.current.get(event)?.delete(handler);
      };
    },
    [],
  );

  return { subscribe };
}
