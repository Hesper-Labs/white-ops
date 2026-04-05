import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { adminApi } from "../api/endpoints";
import { formatDate } from "../lib/utils";
import toast from "react-hot-toast";

const DEMO_USERS = [
  { id: "u1", email: "admin@whiteops.local", full_name: "System Admin", role: "admin", is_active: true, created_at: "2025-03-15T09:00:00Z" },
  { id: "u2", email: "operator@whiteops.local", full_name: "John Operator", role: "operator", is_active: true, created_at: "2025-03-20T10:00:00Z" },
  { id: "u3", email: "viewer@whiteops.local", full_name: "Jane Viewer", role: "viewer", is_active: true, created_at: "2025-03-25T14:00:00Z" },
];

const roleBadge: Record<string, string> = { admin: "badge-red", operator: "badge-blue", viewer: "badge-gray" };

export default function UserManagement() {
  const [showCreate, setShowCreate] = useState(false);

  const { data } = useQuery({
    queryKey: ["users"],
    queryFn: () => adminApi.users(),
  });

  const users = (data?.data?.length ? data.data : DEMO_USERS) as any[];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-neutral-900">User Management</h1>
          <p className="text-xs text-neutral-400 mt-0.5">{users.length} users</p>
        </div>
        <button className="btn-primary flex items-center gap-1.5" onClick={() => setShowCreate(true)}>
          <Plus className="h-3.5 w-3.5" /> Add User
        </button>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr>
              <th className="table-header">Name</th>
              <th className="table-header">Email</th>
              <th className="table-header">Role</th>
              <th className="table-header">Status</th>
              <th className="table-header">Created</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user: any) => (
              <tr key={user.id} className="border-b border-neutral-100 hover:bg-neutral-50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2.5">
                    <div className="h-7 w-7 rounded-md bg-neutral-900 text-white flex items-center justify-center text-xs font-bold">
                      {user.full_name?.[0] ?? "?"}
                    </div>
                    <span className="text-sm font-semibold text-neutral-900">{user.full_name}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-neutral-600">{user.email}</td>
                <td className="px-4 py-3"><span className={roleBadge[user.role] ?? "badge-gray"}>{user.role}</span></td>
                <td className="px-4 py-3">{user.is_active ? <span className="badge-green">active</span> : <span className="badge-red">disabled</span>}</td>
                <td className="px-4 py-3 text-xs text-neutral-400">{formatDate(user.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6 card p-5">
        <h3 className="text-sm font-semibold text-neutral-900 mb-3">Role Permissions</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr>
                <th className="text-left py-2 pr-4 text-neutral-500 font-medium">Permission</th>
                <th className="text-center py-2 px-4 text-neutral-500 font-medium">Admin</th>
                <th className="text-center py-2 px-4 text-neutral-500 font-medium">Operator</th>
                <th className="text-center py-2 px-4 text-neutral-500 font-medium">Viewer</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {[
                ["Create/Edit Agents", true, true, false],
                ["Assign Tasks", true, true, false],
                ["View Dashboard", true, true, true],
                ["Manage Workers", true, false, false],
                ["System Settings", true, false, false],
                ["User Management", true, false, false],
                ["View Audit Logs", true, false, false],
                ["Delete Resources", true, false, false],
              ].map(([perm, admin, operator, viewer]) => (
                <tr key={perm as string}>
                  <td className="py-2 pr-4 text-neutral-700">{perm as string}</td>
                  <td className="py-2 px-4 text-center">{admin ? "Yes" : "-"}</td>
                  <td className="py-2 px-4 text-center">{operator ? "Yes" : "-"}</td>
                  <td className="py-2 px-4 text-center">{viewer ? "Yes" : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="card p-6 w-full max-w-md shadow-lg" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-sm font-bold text-neutral-900 mb-4">Add User</h2>
            <form onSubmit={(e) => { e.preventDefault(); toast.success("User created (demo)"); setShowCreate(false); }} className="space-y-3">
              <div><label className="block text-xs font-medium text-neutral-500 mb-1">Full Name</label><input className="input" required /></div>
              <div><label className="block text-xs font-medium text-neutral-500 mb-1">Email</label><input type="email" className="input" required /></div>
              <div><label className="block text-xs font-medium text-neutral-500 mb-1">Password</label><input type="password" className="input" required /></div>
              <div><label className="block text-xs font-medium text-neutral-500 mb-1">Role</label>
                <select className="input"><option value="viewer">Viewer</option><option value="operator">Operator</option><option value="admin">Admin</option></select>
              </div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" className="btn-primary flex-1">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
