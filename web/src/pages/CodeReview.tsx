import { useState } from "react";
import {
  GitPullRequest,
  Check,
  X,
  MessageSquare,
  ChevronDown,
  ChevronRight,
  Search,
  Filter,
  Plus,
  Minus,
  FileCode,
  Clock,
  Bot,
  AlertTriangle,
} from "lucide-react";
import { codeReviewApi } from "../api/endpoints";

interface DiffHunk {
  old_start: number;
  new_start: number;
  old_lines: string[];
  new_lines: string[];
}

interface ReviewFile {
  path: string;
  additions: number;
  deletions: number;
  hunks: DiffHunk[];
}

interface Review {
  id: string;
  title: string;
  agent: string;
  status: "pending" | "approved" | "changes_requested" | "rejected";
  files_changed: number;
  lines_added: number;
  lines_removed: number;
  created_at: string;
  files: ReviewFile[];
}

const DEMO_REVIEWS: Review[] = [
  {
    id: "1",
    title: "Add user authentication middleware",
    agent: "Developer Agent",
    status: "pending",
    files_changed: 3,
    lines_added: 87,
    lines_removed: 12,
    created_at: "2025-04-07T14:30:00Z",
    files: [
      {
        path: "server/app/core/auth.py",
        additions: 45,
        deletions: 5,
        hunks: [
          {
            old_start: 10,
            new_start: 10,
            old_lines: [
              "def verify(token):",
              "    pass",
            ],
            new_lines: [
              'def verify(token: str) -> dict:',
              '    """Verify JWT token and return payload."""',
              "    try:",
              "        return jwt.decode(token, SECRET_KEY)",
              "    except JWTError:",
              "        raise HTTPException(401)",
            ],
          },
        ],
      },
      {
        path: "server/app/api/v1/auth.py",
        additions: 32,
        deletions: 4,
        hunks: [
          {
            old_start: 1,
            new_start: 1,
            old_lines: [
              "from fastapi import APIRouter",
              "",
              "router = APIRouter()",
            ],
            new_lines: [
              "from fastapi import APIRouter, Depends, HTTPException",
              "from app.core.auth import get_current_user",
              "from app.core.security import create_token",
              "",
              "router = APIRouter()",
            ],
          },
        ],
      },
      {
        path: "server/app/models/user.py",
        additions: 10,
        deletions: 3,
        hunks: [
          {
            old_start: 15,
            new_start: 15,
            old_lines: [
              "    email: str",
              "    name: str",
            ],
            new_lines: [
              "    email: Mapped[str] = mapped_column(String(255), unique=True)",
              "    full_name: Mapped[str] = mapped_column(String(255))",
              "    hashed_password: Mapped[str] = mapped_column(String(255))",
              "    is_active: Mapped[bool] = mapped_column(Boolean, default=True)",
            ],
          },
        ],
      },
    ],
  },
  {
    id: "2",
    title: "Implement cost tracking service",
    agent: "Analyst Agent",
    status: "approved",
    files_changed: 2,
    lines_added: 156,
    lines_removed: 8,
    created_at: "2025-04-06T09:15:00Z",
    files: [
      {
        path: "server/app/services/cost_tracker.py",
        additions: 120,
        deletions: 0,
        hunks: [
          {
            old_start: 1,
            new_start: 1,
            old_lines: [],
            new_lines: [
              '"""Cost tracking service for AI agent operations."""',
              "",
              "from datetime import datetime, timezone",
              "from sqlalchemy.ext.asyncio import AsyncSession",
              "",
              "class CostTracker:",
              '    """Tracks per-agent, per-task, per-provider costs."""',
              "",
              "    async def record_usage(self, agent_id, tokens, provider):",
              "        rate = self._get_rate(provider)",
              "        cost = tokens * rate / 1000",
              "        return cost",
            ],
          },
        ],
      },
      {
        path: "server/app/models/cost.py",
        additions: 36,
        deletions: 8,
        hunks: [
          {
            old_start: 5,
            new_start: 5,
            old_lines: [
              "class CostRecord(Base):",
              '    __tablename__ = "cost_records"',
              "    amount: float",
            ],
            new_lines: [
              "class CostRecord(Base):",
              '    __tablename__ = "cost_records"',
              "    amount: Mapped[float] = mapped_column(Float, default=0.0)",
              "    provider: Mapped[str] = mapped_column(String(50))",
              "    model: Mapped[str] = mapped_column(String(100))",
              "    tokens_used: Mapped[int] = mapped_column(Integer, default=0)",
            ],
          },
        ],
      },
    ],
  },
  {
    id: "3",
    title: "Fix Redis connection pool exhaustion",
    agent: "Developer Agent",
    status: "rejected",
    files_changed: 1,
    lines_added: 23,
    lines_removed: 45,
    created_at: "2025-04-05T16:45:00Z",
    files: [
      {
        path: "server/app/db/redis.py",
        additions: 23,
        deletions: 45,
        hunks: [
          {
            old_start: 20,
            new_start: 20,
            old_lines: [
              "pool = redis.ConnectionPool(",
              "    host=REDIS_HOST,",
              "    port=REDIS_PORT,",
              "    max_connections=10,",
              ")",
            ],
            new_lines: [
              "pool = redis.ConnectionPool(",
              "    host=REDIS_HOST,",
              "    port=REDIS_PORT,",
              "    max_connections=50,",
              "    retry_on_timeout=True,",
              "    socket_keepalive=True,",
              ")",
            ],
          },
        ],
      },
    ],
  },
  {
    id: "4",
    title: "Add workflow DAG validation",
    agent: "Developer Agent",
    status: "changes_requested",
    files_changed: 2,
    lines_added: 64,
    lines_removed: 3,
    created_at: "2025-04-04T11:20:00Z",
    files: [
      {
        path: "server/app/services/workflow_engine.py",
        additions: 50,
        deletions: 2,
        hunks: [
          {
            old_start: 30,
            new_start: 30,
            old_lines: [
              "    def validate(self, steps):",
              "        return True",
            ],
            new_lines: [
              "    def validate(self, steps: list[WorkflowStep]) -> bool:",
              '        """Validate that workflow steps form a valid DAG."""',
              "        graph = self._build_adjacency(steps)",
              "        if self._has_cycle(graph):",
              '            raise ValueError("Workflow contains cycles")',
              "        return True",
            ],
          },
        ],
      },
      {
        path: "server/app/schemas/workflow.py",
        additions: 14,
        deletions: 1,
        hunks: [
          {
            old_start: 10,
            new_start: 10,
            old_lines: [
              "class WorkflowCreate(BaseModel):",
            ],
            new_lines: [
              "class WorkflowCreate(BaseModel):",
              "    name: str",
              "    description: str | None = None",
              "    steps: list[WorkflowStepCreate]",
            ],
          },
        ],
      },
    ],
  },
];

const STATUS_CONFIG: Record<string, { badge: string; label: string }> = {
  pending: { badge: "badge-yellow", label: "Pending" },
  approved: { badge: "badge-green", label: "Approved" },
  changes_requested: { badge: "badge-blue", label: "Changes Requested" },
  rejected: { badge: "badge-red", label: "Rejected" },
};

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function CodeReview() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedReview, setExpandedReview] = useState<string | null>(null);
  const [activeFileTab, setActiveFileTab] = useState<Record<string, number>>({});

  const filtered = DEMO_REVIEWS.filter((r) => {
    if (statusFilter !== "all" && r.status !== statusFilter) return false;
    if (searchQuery && !r.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const handleAction = (reviewId: string, action: string) => {
    if (action === "approve") {
      codeReviewApi.approve(reviewId).catch(() => {});
    } else if (action === "reject" || action === "request_changes") {
      codeReviewApi.reject(reviewId, action).catch(() => {});
    } else if (action === "comment") {
      codeReviewApi.addComment(reviewId, "").catch(() => {});
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <GitPullRequest className="h-5 w-5 text-neutral-500 dark:text-neutral-400 dark:text-neutral-500" />
          <h1 className="text-lg font-bold text-neutral-900 dark:text-neutral-100">Code Reviews</h1>
          <span className="text-xs text-neutral-400 dark:text-neutral-500">{filtered.length} reviews</span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400 dark:text-neutral-500" />
          <input
            type="text"
            placeholder="Search reviews..."
            className="input pl-9"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-1.5">
          <Filter className="h-3.5 w-3.5 text-neutral-400 dark:text-neutral-500" />
          <select
            className="input py-1.5 text-xs"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="changes_requested">Changes Requested</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      {/* Review List */}
      <div className="space-y-2">
        {filtered.map((review) => {
          const isExpanded = expandedReview === review.id;
          const statusConf = STATUS_CONFIG[review.status] ?? { badge: "badge-gray", label: review.status };
          const fileIdx = activeFileTab[review.id] ?? 0;

          return (
            <div key={review.id} className="card overflow-hidden">
              {/* Row header */}
              <button
                onClick={() => setExpandedReview(isExpanded ? null : review.id)}
                className="w-full flex items-center gap-4 p-4 text-left hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors"
              >
                <span className="text-neutral-400 dark:text-neutral-500">
                  {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 truncate">
                      {review.title}
                    </span>
                    <span className={statusConf.badge}>{statusConf.label}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-neutral-400 dark:text-neutral-500">
                    <span className="flex items-center gap-1"><Bot className="h-3 w-3" /> {review.agent}</span>
                    <span className="flex items-center gap-1"><FileCode className="h-3 w-3" /> {review.files_changed} files</span>
                    <span className="text-emerald-500">+{review.lines_added}</span>
                    <span className="text-red-500">-{review.lines_removed}</span>
                    <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {formatDate(review.created_at)}</span>
                  </div>
                </div>
              </button>

              {/* Expanded diff view */}
              {isExpanded && (
                <div className="border-t border-neutral-200 dark:border-neutral-700">
                  {/* Stats bar */}
                  <div className="px-4 py-2 bg-neutral-50 dark:bg-neutral-800/50 flex items-center gap-4 text-xs">
                    <span className="text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">
                      {review.files_changed} file{review.files_changed !== 1 ? "s" : ""} changed
                    </span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                      <Plus className="h-3 w-3" /> {review.lines_added} additions
                    </span>
                    <span className="text-red-600 dark:text-red-400 font-medium flex items-center gap-1">
                      <Minus className="h-3 w-3" /> {review.lines_removed} deletions
                    </span>
                  </div>

                  {/* File tabs */}
                  {review.files.length > 1 && (
                    <div className="flex border-b border-neutral-200 dark:border-neutral-700 overflow-x-auto">
                      {review.files.map((file, idx) => (
                        <button
                          key={file.path}
                          onClick={() => setActiveFileTab((prev) => ({ ...prev, [review.id]: idx }))}
                          className={`px-3 py-2 text-xs font-mono whitespace-nowrap border-b-2 transition-colors ${
                            fileIdx === idx
                              ? "border-neutral-900 dark:border-neutral-100 text-neutral-900 dark:text-neutral-100"
                              : "border-transparent text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                          }`}
                        >
                          {file.path.split("/").pop()}
                          <span className="ml-2 text-[10px]">
                            <span className="text-emerald-500">+{file.additions}</span>
                            {" "}
                            <span className="text-red-500">-{file.deletions}</span>
                          </span>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* File path header */}
                  <div className="px-4 py-1.5 bg-neutral-100 dark:bg-neutral-800 text-xs font-mono text-neutral-600 dark:text-neutral-400 flex items-center gap-2">
                    <FileCode className="h-3 w-3" />
                    {review.files[fileIdx]?.path}
                  </div>

                  {/* Diff content */}
                  <div className="overflow-x-auto">
                    {review.files[fileIdx]?.hunks.map((hunk, hunkIdx) => (
                      <div key={hunkIdx}>
                        <div className="px-4 py-1 bg-blue-50 dark:bg-blue-900/20 text-xs text-blue-600 dark:text-blue-400 font-mono">
                          @@ -{hunk.old_start},{hunk.old_lines.length} +{hunk.new_start},{hunk.new_lines.length} @@
                        </div>
                        <table className="w-full font-mono text-xs">
                          <tbody>
                            {/* Removed lines */}
                            {hunk.old_lines.map((line, lineIdx) => (
                              <tr key={`old-${lineIdx}`} className="bg-red-50 dark:bg-red-900/15">
                                <td className="w-10 text-right pr-2 text-neutral-400 dark:text-neutral-500 select-none border-r border-neutral-200 dark:border-neutral-700 py-0.5 px-2">
                                  {hunk.old_start + lineIdx}
                                </td>
                                <td className="w-10 text-right pr-2 text-neutral-400 dark:text-neutral-500 select-none border-r border-neutral-200 dark:border-neutral-700 py-0.5 px-2">
                                </td>
                                <td className="px-3 py-0.5 whitespace-pre text-red-700 dark:text-red-300">
                                  <span className="select-none text-red-400 mr-2">-</span>{line}
                                </td>
                              </tr>
                            ))}
                            {/* Added lines */}
                            {hunk.new_lines.map((line, lineIdx) => (
                              <tr key={`new-${lineIdx}`} className="bg-emerald-50 dark:bg-emerald-900/15">
                                <td className="w-10 text-right pr-2 text-neutral-400 dark:text-neutral-500 select-none border-r border-neutral-200 dark:border-neutral-700 py-0.5 px-2">
                                </td>
                                <td className="w-10 text-right pr-2 text-neutral-400 dark:text-neutral-500 select-none border-r border-neutral-200 dark:border-neutral-700 py-0.5 px-2">
                                  {hunk.new_start + lineIdx}
                                </td>
                                <td className="px-3 py-0.5 whitespace-pre text-emerald-700 dark:text-emerald-300">
                                  <span className="select-none text-emerald-400 mr-2">+</span>{line}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ))}
                  </div>

                  {/* Action bar */}
                  <div className="px-4 py-3 border-t border-neutral-200 dark:border-neutral-700 flex items-center gap-2">
                    {review.status === "pending" && (
                      <>
                        <button
                          onClick={() => handleAction(review.id, "approve")}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
                        >
                          <Check className="h-3.5 w-3.5" /> Approve
                        </button>
                        <button
                          onClick={() => handleAction(review.id, "request_changes")}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-amber-500 text-white hover:bg-amber-600 transition-colors"
                        >
                          <AlertTriangle className="h-3.5 w-3.5" /> Request Changes
                        </button>
                        <button
                          onClick={() => handleAction(review.id, "reject")}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
                        >
                          <X className="h-3.5 w-3.5" /> Reject
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => handleAction(review.id, "comment")}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-neutral-600 dark:text-neutral-300 bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-colors ml-auto"
                    >
                      <MessageSquare className="h-3.5 w-3.5" /> Comment
                    </button>
                  </div>

                  {/* Comments placeholder */}
                  <div className="px-4 py-3 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/30">
                    <p className="text-xs text-neutral-400 dark:text-neutral-500 dark:text-neutral-400 dark:text-neutral-500">
                      No comments yet. Add a comment to start the discussion.
                    </p>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="card p-12 text-center">
            <GitPullRequest className="h-10 w-10 text-neutral-300 dark:text-neutral-600 mx-auto mb-3" />
            <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400 dark:text-neutral-500">No code reviews found</p>
            <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
              Code reviews will appear here when agents make code changes.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
