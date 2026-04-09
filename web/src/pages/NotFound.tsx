import { useNavigate } from "react-router-dom";
import { Home, ArrowLeft } from "lucide-react";

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8">
      <div className="text-6xl font-bold text-neutral-200 dark:text-neutral-700 mb-4">404</div>
      <h1 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">
        Page Not Found
      </h1>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6 max-w-md">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md border border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Go Back
        </button>
        <button
          onClick={() => navigate("/")}
          className="btn-primary flex items-center gap-1.5 text-xs px-3 py-1.5"
        >
          <Home className="h-3.5 w-3.5" />
          Dashboard
        </button>
      </div>
    </div>
  );
}
