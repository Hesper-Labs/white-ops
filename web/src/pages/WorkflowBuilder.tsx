import { useState } from "react";
import { Plus, Trash2, ArrowDown, Play, Save, GitBranch } from "lucide-react";
import toast from "react-hot-toast";

interface WorkflowStep {
  id: string;
  name: string;
  type: "task" | "condition" | "parallel" | "wait" | "notify";
  agent: string;
  config: string;
}

const STEP_TYPES = [
  { value: "task", label: "Task", color: "bg-blue-50 border-blue-200 text-blue-700" },
  { value: "condition", label: "If/Else", color: "bg-amber-50 border-amber-200 text-amber-700" },
  { value: "parallel", label: "Parallel", color: "bg-violet-50 border-violet-200 text-violet-700" },
  { value: "wait", label: "Wait", color: "bg-neutral-50 border-neutral-200 text-neutral-600" },
  { value: "notify", label: "Notify", color: "bg-emerald-50 border-emerald-200 text-emerald-700" },
];

const AGENTS = ["Research Agent", "Data Analyst", "Office Assistant", "Developer Bot", "Auto-assign"];

export default function WorkflowBuilder() {
  const [name, setName] = useState("New Workflow");
  const [steps, setSteps] = useState<WorkflowStep[]>([
    { id: "1", name: "Collect Data", type: "task", agent: "Research Agent", config: "Scrape competitor pricing from websites" },
    { id: "2", name: "Analyze Data", type: "task", agent: "Data Analyst", config: "Run statistical analysis on collected data" },
    { id: "3", name: "Check Results", type: "condition", agent: "Auto-assign", config: "If data quality > 90% continue, else retry step 1" },
    { id: "4", name: "Generate Report", type: "task", agent: "Office Assistant", config: "Create PDF report with charts and summary" },
    { id: "5", name: "Send Notification", type: "notify", agent: "Auto-assign", config: "Email report to management team" },
  ]);

  const addStep = () => {
    setSteps([...steps, {
      id: String(Date.now()),
      name: "New Step",
      type: "task",
      agent: "Auto-assign",
      config: "",
    }]);
  };

  const removeStep = (id: string) => {
    setSteps(steps.filter(s => s.id !== id));
  };

  const updateStep = (id: string, field: keyof WorkflowStep, value: string) => {
    setSteps(steps.map(s => s.id === id ? { ...s, [field]: value } : s));
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <GitBranch className="h-5 w-5 text-neutral-400 dark:text-neutral-500" />
          <input
            className="text-lg font-bold text-neutral-900 bg-transparent border-none focus:outline-none focus:ring-0 p-0"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary flex items-center gap-1.5" onClick={() => toast.success("Workflow saved (demo)")}>
            <Save className="h-3.5 w-3.5" /> Save
          </button>
          <button className="btn-primary flex items-center gap-1.5" onClick={() => toast.success("Workflow started (demo)")}>
            <Play className="h-3.5 w-3.5" /> Run
          </button>
        </div>
      </div>

      <div className="max-w-2xl mx-auto">
        {steps.map((step, index) => {
          const typeInfo = STEP_TYPES.find(t => t.value === step.type) ?? STEP_TYPES[0]!;
          return (
            <div key={step.id}>
              <div className="card p-4 relative group">
                <div className="flex items-start gap-3">
                  {/* Step number */}
                  <div className="w-7 h-7 rounded-md bg-neutral-100 flex items-center justify-center text-xs font-bold text-neutral-500 flex-shrink-0 mt-1">
                    {index + 1}
                  </div>

                  <div className="flex-1 space-y-2">
                    {/* Step name + type */}
                    <div className="flex items-center gap-2">
                      <input
                        className="text-sm font-semibold text-neutral-900 bg-transparent border-none focus:outline-none p-0 flex-1"
                        value={step.name}
                        onChange={(e) => updateStep(step.id, "name", e.target.value)}
                      />
                      <select
                        className="text-[11px] font-semibold px-2 py-0.5 rounded border appearance-none cursor-pointer pr-5"
                        style={{ backgroundImage: "none" }}
                        value={step.type}
                        onChange={(e) => updateStep(step.id, "type", e.target.value as WorkflowStep["type"])}
                      >
                        {STEP_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                      </select>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${typeInfo.color}`}>
                        {typeInfo.label}
                      </span>
                    </div>

                    {/* Agent + Config */}
                    <div className="flex gap-2">
                      <select
                        className="input text-xs py-1.5 w-40"
                        value={step.agent}
                        onChange={(e) => updateStep(step.id, "agent", e.target.value)}
                      >
                        {AGENTS.map(a => <option key={a} value={a}>{a}</option>)}
                      </select>
                      <input
                        className="input text-xs py-1.5 flex-1"
                        placeholder="Step instructions..."
                        value={step.config}
                        onChange={(e) => updateStep(step.id, "config", e.target.value)}
                      />
                    </div>
                  </div>

                  {/* Delete */}
                  <button
                    onClick={() => removeStep(step.id)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity btn-ghost text-red-400 hover:text-red-600 mt-1"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              {/* Arrow connector */}
              {index < steps.length - 1 && (
                <div className="flex justify-center py-1">
                  <ArrowDown className="h-4 w-4 text-neutral-300" />
                </div>
              )}
            </div>
          );
        })}

        {/* Add step button */}
        <div className="flex justify-center mt-4">
          <button
            onClick={addStep}
            className="btn-secondary flex items-center gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" /> Add Step
          </button>
        </div>
      </div>
    </div>
  );
}
