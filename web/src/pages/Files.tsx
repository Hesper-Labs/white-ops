import { useQuery } from "@tanstack/react-query";
import { FolderOpen, FileText } from "lucide-react";
import { filesApi } from "../api/endpoints";
import { formatDate, formatBytes } from "../lib/utils";

export default function Files() {
  const { data, isLoading } = useQuery({
    queryKey: ["files"],
    queryFn: () => filesApi.list(),
  });

  const files = data?.data ?? [];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Files</h1>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      ) : files.length === 0 ? (
        <div className="card p-12 text-center">
          <FolderOpen className="h-12 w-12 text-surface-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-surface-700">No files yet</h3>
          <p className="text-surface-400 mt-1">Files created by agents will appear here.</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="bg-surface-50 border-b border-surface-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-medium text-surface-500 uppercase">Name</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-surface-500 uppercase">Type</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-surface-500 uppercase">Size</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-surface-500 uppercase">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {files.map((file: any) => (
                <tr key={file.id as string} className="hover:bg-surface-50">
                  <td className="px-4 py-3 flex items-center gap-2">
                    <FileText className="h-4 w-4 text-surface-400" />
                    <span className="text-sm font-medium">{file.filename as string}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-surface-500">{file.content_type as string}</td>
                  <td className="px-4 py-3 text-sm text-surface-500">{formatBytes(file.size_bytes as number)}</td>
                  <td className="px-4 py-3 text-sm text-surface-500">{formatDate(file.created_at as string)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
