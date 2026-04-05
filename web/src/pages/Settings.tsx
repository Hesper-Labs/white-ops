import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Settings as SettingsIcon,
  Key,
  Mail,
  Shield,
  Bell,
  HardDrive,
  CheckCircle,
  XCircle,
  RefreshCw,
  Save,
} from "lucide-react";
import { settingsApi } from "../api/endpoints";
import toast from "react-hot-toast";

interface SettingField {
  value: string;
  description: string;
  is_secret: boolean;
  is_default: boolean;
}

const categoryIcons: Record<string, React.ElementType> = {
  llm: Key,
  email: Mail,
  security: Shield,
  general: SettingsIcon,
  notifications: Bell,
  storage: HardDrive,
};

const categoryLabels: Record<string, string> = {
  llm: "LLM Configuration",
  email: "Email Settings",
  security: "Security",
  general: "General",
  notifications: "Notifications",
  storage: "Storage",
};

export default function Settings() {
  const [pendingChanges, setPendingChanges] = useState<Record<string, string>>({});
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: () => settingsApi.getAll(),
  });

  const { data: healthData } = useQuery({
    queryKey: ["system-health"],
    queryFn: () => settingsApi.health(),
    refetchInterval: 30000,
  });

  const saveMutation = useMutation({
    mutationFn: () => settingsApi.bulkUpdate(pendingChanges),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      setPendingChanges({});
      toast.success("Settings saved");
    },
    onError: () => toast.error("Failed to save settings"),
  });

  const handleChange = (category: string, key: string, value: string) => {
    setPendingChanges((prev) => ({
      ...prev,
      [`${category}.${key}`]: value,
    }));
  };

  const settings = data?.data ?? {};
  const health = healthData?.data;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Settings</h1>
        <div className="flex gap-3">
          {Object.keys(pendingChanges).length > 0 && (
            <span className="text-sm text-orange-600 self-center">
              {Object.keys(pendingChanges).length} unsaved changes
            </span>
          )}
          <button
            className="btn-primary flex items-center gap-2"
            onClick={() => saveMutation.mutate()}
            disabled={Object.keys(pendingChanges).length === 0 || saveMutation.isPending}
          >
            <Save className="h-4 w-4" />
            {saveMutation.isPending ? "Saving..." : "Save All"}
          </button>
        </div>
      </div>

      {/* System Health */}
      {health && (
        <div className="card p-5 mb-6">
          <div className="flex items-center gap-3 mb-4">
            <RefreshCw className="h-5 w-5 text-primary-600" />
            <h2 className="text-lg font-semibold">System Health</h2>
            <span
              className={
                health.overall === "healthy" ? "badge-green" : "badge-red"
              }
            >
              {health.overall}
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(
              health.components as Record<
                string,
                { status: string; type?: string; error?: string }
              >,
            ).map(([name, info]) => (
              <div
                key={name}
                className="flex items-center gap-2 p-3 bg-surface-50 rounded-lg"
              >
                {info.status === "healthy" ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
                <div>
                  <p className="text-sm font-medium capitalize">{name}</p>
                  <p className="text-xs text-surface-400">
                    {info.type ?? info.status}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Settings Categories */}
      <div className="space-y-6 max-w-3xl">
        {Object.entries(settings as Record<string, Record<string, SettingField>>).map(
          ([category, fields]) => {
            const Icon = categoryIcons[category] ?? SettingsIcon;
            return (
              <div key={category} className="card p-6">
                <div className="flex items-center gap-3 mb-4">
                  <Icon className="h-5 w-5 text-primary-600" />
                  <h2 className="text-lg font-semibold">
                    {categoryLabels[category] ?? category}
                  </h2>
                </div>
                <div className="space-y-4">
                  {Object.entries(fields).map(([key, field]) => {
                    const fullKey = `${category}.${key}`;
                    const currentValue =
                      pendingChanges[fullKey] ?? field.value;
                    const isChanged = fullKey in pendingChanges;

                    return (
                      <div key={key}>
                        <label className="block text-sm font-medium mb-1">
                          {key
                            .replace(/_/g, " ")
                            .replace(/\b\w/g, (l) => l.toUpperCase())}
                          {field.is_default && (
                            <span className="text-xs text-surface-400 ml-2">
                              (default)
                            </span>
                          )}
                          {isChanged && (
                            <span className="text-xs text-orange-500 ml-2">
                              (modified)
                            </span>
                          )}
                        </label>
                        <p className="text-xs text-surface-400 mb-1">
                          {field.description}
                        </p>
                        {key.includes("enabled") ||
                        key.includes("mode") ||
                        field.value === "true" ||
                        field.value === "false" ? (
                          <select
                            className="input max-w-xs"
                            value={currentValue}
                            onChange={(e) =>
                              handleChange(category, key, e.target.value)
                            }
                          >
                            <option value="true">Enabled</option>
                            <option value="false">Disabled</option>
                          </select>
                        ) : key.includes("provider") ? (
                          <select
                            className="input max-w-xs"
                            value={currentValue}
                            onChange={(e) =>
                              handleChange(category, key, e.target.value)
                            }
                          >
                            <option value="anthropic">
                              Anthropic (Claude)
                            </option>
                            <option value="openai">OpenAI (GPT)</option>
                            <option value="google">Google (Gemini)</option>
                            <option value="ollama">Ollama (Local)</option>
                          </select>
                        ) : key.includes("level") ? (
                          <select
                            className="input max-w-xs"
                            value={currentValue}
                            onChange={(e) =>
                              handleChange(category, key, e.target.value)
                            }
                          >
                            <option value="DEBUG">DEBUG</option>
                            <option value="INFO">INFO</option>
                            <option value="WARNING">WARNING</option>
                            <option value="ERROR">ERROR</option>
                          </select>
                        ) : (
                          <input
                            type={field.is_secret ? "password" : "text"}
                            className={`input max-w-md ${isChanged ? "border-orange-400" : ""}`}
                            value={currentValue}
                            onChange={(e) =>
                              handleChange(category, key, e.target.value)
                            }
                            placeholder={field.is_secret ? "Enter new value..." : ""}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          },
        )}
      </div>
    </div>
  );
}
