import { AlertTriangle } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";

export function DemoBanner() {
  const demoMode = useAuthStore((s) => s.demoMode);

  if (!demoMode) return null;

  return (
    <div
      role="alert"
      className="bg-amber-50 dark:bg-amber-900/30 border-b border-amber-200 dark:border-amber-800 px-4 py-2 flex items-center gap-2 text-amber-800 dark:text-amber-200"
    >
      <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span className="text-xs font-medium">
        Demo Mode - Backend is unavailable. You are viewing sample data. Changes will not be saved.
      </span>
    </div>
  );
}
