import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { LogIn, Rocket, Eye, EyeOff } from "lucide-react";
import toast from "react-hot-toast";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isFirstRun, setIsFirstRun] = useState(false);
  const { login, user } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    // Check if this is a first-time setup
    const setupDone = localStorage.getItem("whiteops_setup_complete");
    if (!setupDone) setIsFirstRun(true);
    // If already logged in, redirect
    if (user) navigate("/");
  }, [user, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch {
      toast.error("Invalid email or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 dark:bg-neutral-950 px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-neutral-900 dark:bg-white mb-4">
            <LogIn className="h-6 w-6 text-white dark:text-neutral-900" />
          </div>
          <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">
            White-Ops
          </h1>
          <p className="text-xs text-neutral-400 mt-1 uppercase tracking-wider">
            AI Workforce Platform
          </p>
        </div>

        {/* First run banner */}
        {isFirstRun && (
          <Link
            to="/setup"
            className="flex items-center gap-3 p-4 mb-6 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
          >
            <div className="h-9 w-9 rounded-lg bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center flex-shrink-0">
              <Rocket className="h-4 w-4 text-neutral-600 dark:text-neutral-400 dark:text-neutral-500" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                First time? Run the Setup Wizard
              </p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">
                Configure admin account, LLM provider, and deploy workers
              </p>
            </div>
            <span className="text-xs font-medium text-neutral-400 dark:text-neutral-500">&rarr;</span>
          </Link>
        )}

        {/* Login form */}
        <div className="bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-lg p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-neutral-600 dark:text-neutral-400 mb-1.5">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input w-full dark:bg-neutral-800 dark:border-neutral-700 dark:text-neutral-100"
                placeholder="admin@whiteops.local"
                autoFocus
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-600 dark:text-neutral-400 mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input w-full pr-10 dark:bg-neutral-800 dark:border-neutral-700 dark:text-neutral-100"
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading || !email || !password}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {loading ? (
                <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <LogIn className="h-4 w-4" />
              )}
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>
        </div>

        <p className="text-center text-[11px] text-neutral-400 dark:text-neutral-500 mt-5">
          No backend? Sign in with any credentials to enter demo mode.
        </p>
      </div>
    </div>
  );
}
