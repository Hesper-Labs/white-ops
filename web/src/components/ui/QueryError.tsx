import { AlertTriangle, RefreshCw, WifiOff } from "lucide-react";

interface QueryErrorProps {
  error: Error | null;
  onRetry?: () => void;
  message?: string;
}

export function QueryError({ error, onRetry, message }: QueryErrorProps) {
  const isNetworkError = error?.message?.includes("Network Error") || error?.message?.includes("ERR_CONNECTION");

  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center p-8 text-center"
    >
      {isNetworkError ? (
        <WifiOff className="h-10 w-10 text-neutral-400 dark:text-neutral-500 mb-3" aria-hidden="true" />
      ) : (
        <AlertTriangle className="h-10 w-10 text-red-400 dark:text-red-500 mb-3" aria-hidden="true" />
      )}
      <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-1">
        {isNetworkError ? "Connection Error" : "Something went wrong"}
      </h3>
      <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-4 max-w-sm">
        {message || error?.message || "An unexpected error occurred. Please try again."}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="btn-primary text-xs flex items-center gap-1.5 px-3 py-1.5"
          aria-label="Retry loading data"
        >
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          Retry
        </button>
      )}
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ElementType;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({ title, description, icon: Icon, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      {Icon && <Icon className="h-10 w-10 text-neutral-300 dark:text-neutral-600 mb-3" aria-hidden="true" />}
      <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-1">{title}</h3>
      {description && (
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-4 max-w-sm">{description}</p>
      )}
      {action && (
        <button onClick={action.onClick} className="btn-primary text-xs px-3 py-1.5">
          {action.label}
        </button>
      )}
    </div>
  );
}
