import { useState } from "react";
import { Copy, Plus } from "lucide-react";
import toast from "react-hot-toast";

const DEMO_TEMPLATES = [
  { id: "tt1", name: "Weekly Sales Report", category: "Reports", description: "Generate comprehensive weekly sales report with charts, trends, and comparisons", tools: ["excel", "data_analysis", "data_visualization", "report_generator"], priority: "high", instructions: "1. Pull sales data from the database\n2. Create Excel with pivot tables\n3. Generate charts for revenue, units, and regional breakdown\n4. Create PDF report with executive summary\n5. Email to management team" },
  { id: "tt2", name: "Competitor Analysis", category: "Research", description: "Research and compare competitor products, pricing, and market positioning", tools: ["browser", "web_search", "web_scraper", "excel"], priority: "medium", instructions: "1. Search for competitor websites\n2. Scrape product listings and pricing\n3. Compare features side by side\n4. Create Excel comparison matrix\n5. Write summary report" },
  { id: "tt3", name: "New Client Onboarding", category: "Operations", description: "Complete onboarding workflow for new clients including CRM, documents, and email", tools: ["crm", "word", "external_email", "calendar"], priority: "medium", instructions: "1. Create client entry in CRM\n2. Generate welcome packet (Word)\n3. Send welcome email with attachments\n4. Schedule kickoff meeting\n5. Create project folder" },
  { id: "tt4", name: "Invoice Generation", category: "Finance", description: "Generate monthly invoices for active clients", tools: ["invoice", "crm", "external_email", "pdf"], priority: "high", instructions: "1. Pull active client list from CRM\n2. Calculate billing for each client\n3. Generate PDF invoices\n4. Email invoices to clients\n5. Update CRM with invoice dates" },
  { id: "tt5", name: "Code Review", category: "Technical", description: "Review recent code changes for bugs, security issues, and best practices", tools: ["git_ops", "code_review", "github"], priority: "medium", instructions: "1. Clone repository or pull latest\n2. Review recent commits\n3. Run code analysis\n4. Create GitHub issues for findings\n5. Write summary report" },
  { id: "tt6", name: "Employee Monthly Report", category: "HR", description: "Generate monthly HR report with attendance, leave, and performance data", tools: ["leave_manager", "employee_directory", "excel", "report_generator"], priority: "low", instructions: "1. Pull attendance data\n2. Summarize leave requests\n3. Calculate performance metrics\n4. Create Excel summary\n5. Generate PDF report" },
];

export default function TaskTemplates() {
  const [selectedCategory, setSelectedCategory] = useState("");
  const categories = [...new Set(DEMO_TEMPLATES.map(t => t.category))];
  const filtered = selectedCategory ? DEMO_TEMPLATES.filter(t => t.category === selectedCategory) : DEMO_TEMPLATES;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-neutral-900">Task Templates</h1>
          <p className="text-xs text-neutral-400 mt-0.5">{DEMO_TEMPLATES.length} templates available</p>
        </div>
        <button className="btn-primary flex items-center gap-1.5"><Plus className="h-3.5 w-3.5" /> New Template</button>
      </div>

      <div className="flex gap-2 mb-4">
        <button onClick={() => setSelectedCategory("")} className={`px-3 py-1.5 rounded-md text-xs font-medium ${!selectedCategory ? "bg-neutral-900 text-white" : "bg-white text-neutral-600 border border-neutral-300 hover:bg-neutral-50"}`}>All</button>
        {categories.map(c => (
          <button key={c} onClick={() => setSelectedCategory(c)} className={`px-3 py-1.5 rounded-md text-xs font-medium ${selectedCategory === c ? "bg-neutral-900 text-white" : "bg-white text-neutral-600 border border-neutral-300 hover:bg-neutral-50"}`}>{c}</button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filtered.map(t => (
          <div key={t.id} className="card p-5">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="text-sm font-semibold text-neutral-900">{t.name}</h3>
                <span className="text-[11px] text-neutral-400">{t.category}</span>
              </div>
              <span className={t.priority === "high" ? "badge-red" : t.priority === "medium" ? "badge-yellow" : "badge-gray"}>{t.priority}</span>
            </div>
            <p className="text-xs text-neutral-500 mb-3">{t.description}</p>
            <div className="flex flex-wrap gap-1 mb-3">
              {t.tools.map(tool => (
                <span key={tool} className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-100 text-neutral-500 font-mono">{tool}</span>
              ))}
            </div>
            <div className="flex gap-2">
              <button onClick={() => toast.success("Task created from template (demo)")} className="btn-primary text-xs flex items-center gap-1 flex-1">
                <Copy className="h-3 w-3" /> Use Template
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
