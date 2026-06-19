"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import {
  ShieldCheck, Users, Search, Plus, UserCheck, Mail,
  Edit, Trash2, Key, X, CheckCircle, Loader2, AlertCircle, RefreshCw,
} from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import AICopilot from "@/components/AICopilot";
import { cn } from "@/lib/utils";
import { usersApi, type User } from "@/lib/api";

export default function AdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [userToEdit, setUserToEdit] = useState<User | null>(null);
  const [resetUserId, setResetUserId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Invite form
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newRole, setNewRole] = useState("viewer");
  const [newPassword, setNewPassword] = useState("");

  // Reset form
  const [newPw, setNewPw] = useState("");

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await usersApi.list();
      setUsers(data);
    } catch (err: any) {
      setError(err.message || "Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase());
    const matchesRole = roleFilter === "all" || u.role.toLowerCase() === roleFilter;
    const matchesStatus = statusFilter === "all" || u.status.toLowerCase() === statusFilter;
    return matchesSearch && matchesRole && matchesStatus;
  });

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this user?")) return;
    try {
      await usersApi.delete(id);
      setUsers(users.filter((u) => u.id !== id));
    } catch (err: any) {
      alert(`Failed to delete user: ${err.message}`);
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName || !newEmail || !newPassword) return;
    setSubmitting(true);
    try {
      const res = await usersApi.create({ email: newEmail, password: newPassword, name: newName, role: newRole });
      await fetchUsers(); // Refresh to get the new user from DB
      setIsInviteModalOpen(false);
      setNewName(""); setNewEmail(""); setNewRole("viewer"); setNewPassword("");
    } catch (err: any) {
      alert(`Failed to create user: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const openEditModal = (user: User) => {
    setUserToEdit({ ...user });
    setIsEditModalOpen(true);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userToEdit) return;
    setSubmitting(true);
    try {
      await usersApi.update(userToEdit.id, { role: userToEdit.role, name: userToEdit.name });
      setUsers(users.map((u) => (u.id === userToEdit.id ? { ...u, role: userToEdit.role, name: userToEdit.name } : u)));
      setIsEditModalOpen(false);
      setUserToEdit(null);
    } catch (err: any) {
      alert(`Failed to update user: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const openResetModal = (id: string) => {
    setResetUserId(id);
    setNewPw("");
    setIsResetModalOpen(true);
  };

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetUserId || !newPw) return;
    setSubmitting(true);
    try {
      await usersApi.resetPassword(resetUserId, newPw);
      setIsResetModalOpen(false);
      setResetUserId(null);
      setNewPw("");
      alert("Password reset successfully.");
    } catch (err: any) {
      alert(`Failed to reset password: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass =
    "w-full px-4 py-3 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400 transition-all";
  const labelClass = "block text-xs font-semibold text-slate-700 mb-1.5";

  const avatarColors = [
    "from-blue-500 to-blue-700", "from-violet-500 to-violet-700",
    "from-emerald-500 to-emerald-700", "from-amber-500 to-amber-700",
    "from-pink-500 to-pink-700", "from-slate-500 to-slate-700",
  ];
  const getAvatar = (u: User) => {
    const initials = (u.name || u.email).split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2);
    const color = avatarColors[parseInt(u.id, 10) % avatarColors.length];
    return { initials, color };
  };

  return (
    <AppShell breadcrumbs={[{ label: "Administration" }, { label: "User Management" }]}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">User Management</h1>
            <p className="text-slate-500 text-sm mt-1">Manage platform access, roles, and permissions.</p>
          </div>
          <motion.button onClick={() => setIsInviteModalOpen(true)} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-bold text-white rounded-xl shadow-lg shadow-violet-500/25 btn-shine"
            style={{ background: "linear-gradient(135deg, #7c3aed, #6d28d9)" }}>
            <Plus className="w-4 h-4" /> Invite User
          </motion.button>
        </motion.div>

        {/* Stats Row */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            { label: "Total Users", value: users.length, icon: Users, color: "violet" },
            { label: "Active Users", value: users.filter((u) => u.status === "Active").length, icon: UserCheck, color: "emerald" },
            { label: "Admins", value: users.filter((u) => u.role === "admin").length, icon: ShieldCheck, color: "blue" },
            { label: "Pending Invites", value: users.filter((u) => u.status === "Pending").length, icon: Mail, color: "amber" },
          ].map((stat, i) => (
            <motion.div key={stat.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
              className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3 mb-3">
                <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center",
                  stat.color === "violet" ? "bg-violet-50 text-violet-600" :
                  stat.color === "emerald" ? "bg-emerald-50 text-emerald-600" :
                  stat.color === "blue" ? "bg-blue-50 text-blue-600" : "bg-amber-50 text-amber-600")}>
                  <stat.icon className="w-4 h-4" />
                </div>
                <p className="text-xs text-slate-500 font-medium">{stat.label}</p>
              </div>
              <p className="text-2xl font-bold text-slate-900">{stat.value}</p>
            </motion.div>
          ))}
        </div>

        {/* Search & Filters */}
        <div className="bg-white p-4 rounded-t-2xl border border-slate-200 border-b-0 flex items-center justify-between">
          <div className="relative w-96">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input type="text" placeholder="Search users by name or email..." value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400 transition-all" />
          </div>
          <div className="flex gap-2">
            <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}
              className="px-4 py-2 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400 text-slate-700 font-medium">
              <option value="all">All Roles</option>
              <option value="admin">Admin</option>
              <option value="estimator">Estimator</option>
              <option value="viewer">Viewer</option>
            </select>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400 text-slate-700 font-medium">
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
            <button onClick={fetchUsers} title="Refresh"
              className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition-colors">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Users Table */}
        <div className="bg-white rounded-b-2xl border border-slate-200 shadow-sm overflow-hidden mb-6">
          {loading ? (
            <div className="flex items-center justify-center py-16 text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin mr-2" />
              <span className="text-sm">Loading users from database...</span>
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 m-4 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl">
              <AlertCircle className="w-4 h-4" /> {error}
              <button onClick={fetchUsers} className="ml-auto text-xs underline">Retry</button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/50">
                    {["User", "Role", "Status", "Created", "Actions"].map((h) => (
                      <th key={h} className="text-left px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {filteredUsers.length === 0 && (
                    <tr><td colSpan={5} className="text-center py-8 text-sm text-slate-500">No users found matching your filters.</td></tr>
                  )}
                  {filteredUsers.map((user, i) => {
                    const { initials, color } = getAvatar(user);
                    return (
                      <motion.tr key={user.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
                        className="table-row-hover transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm bg-gradient-to-br ${color}`}>
                              {initials}
                            </div>
                            <div>
                              <p className="text-sm font-bold text-slate-900">{user.name || "—"}</p>
                              <p className="text-xs text-slate-500">{user.email}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className={cn("px-2.5 py-1 text-xs font-bold rounded-lg border",
                            user.role === "admin" ? "bg-red-50 text-red-700 border-red-100" :
                            user.role === "estimator" ? "bg-blue-50 text-blue-700 border-blue-100" :
                            "bg-emerald-50 text-emerald-700 border-emerald-100")}>
                            {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className={cn("flex items-center gap-1.5 text-xs font-medium",
                            user.status === "Active" ? "text-emerald-600" : "text-slate-400")}>
                            <span className={cn("w-1.5 h-1.5 rounded-full",
                              user.status === "Active" ? "bg-emerald-500" : "bg-slate-300")} />
                            {user.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-xs text-slate-500">
                          {user.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={() => openEditModal(user)} title="Edit User"
                              className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                              <Edit className="w-4 h-4" />
                            </button>
                            <button onClick={() => openResetModal(user.id)} title="Reset Password"
                              className="p-1.5 text-slate-400 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition-colors">
                              <Key className="w-4 h-4" />
                            </button>
                            {user.role !== "admin" && (
                              <button onClick={() => handleDelete(user.id)} title="Delete User"
                                className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </td>
                      </motion.tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Role Permissions Summary */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <h3 className="text-sm font-bold text-slate-900 mb-4">Role Permissions Summary</h3>
          <div className="grid grid-cols-3 gap-4">
            {[
              { role: "Admin", badge: "bg-red-100 text-red-700", desc: "Full access: view_all, create_client, delete_client, create_estimate, delete_estimate, manage_users." },
              { role: "Estimator", badge: "bg-blue-100 text-blue-700", desc: "Standard access: view_all, create_client, create_estimate. Cannot delete records or manage users." },
              { role: "Viewer", badge: "bg-emerald-100 text-emerald-700", desc: "Read-only access: view_all. Can view all estimates and reports but cannot modify data." },
            ].map((r) => (
              <div key={r.role} className="p-4 rounded-xl border border-slate-100 bg-slate-50">
                <span className={`px-2 py-1 text-xs font-bold rounded-lg mb-2 inline-block ${r.badge}`}>{r.role}</span>
                <p className="text-xs text-slate-600 leading-relaxed">{r.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Invite Modal ── */}
      <AnimatePresence>
        {isInviteModalOpen && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setIsInviteModalOpen(false)}
              className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50" />
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-white rounded-2xl shadow-xl z-50">
              <div className="p-6 border-b border-slate-100 flex items-center justify-between">
                <h2 className="text-lg font-bold text-slate-900">Invite New User</h2>
                <button onClick={() => setIsInviteModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleInvite} className="p-6 space-y-4">
                <div><label className={labelClass}>Full Name</label>
                  <input type="text" required value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Jane Doe" className={inputClass} /></div>
                <div><label className={labelClass}>Email Address</label>
                  <input type="email" required value={newEmail} onChange={(e) => setNewEmail(e.target.value)} placeholder="jane@company.com" className={inputClass} /></div>
                <div><label className={labelClass}>Password</label>
                  <input type="password" required minLength={6} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="Min. 6 characters" className={inputClass} /></div>
                <div><label className={labelClass}>Role</label>
                  <select value={newRole} onChange={(e) => setNewRole(e.target.value)} className={inputClass}>
                    <option value="viewer">Viewer</option>
                    <option value="estimator">Estimator</option>
                    <option value="admin">Admin</option>
                  </select></div>
                <div className="pt-2 flex gap-3">
                  <button type="button" onClick={() => setIsInviteModalOpen(false)} className="flex-1 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50 rounded-xl border border-slate-200">Cancel</button>
                  <button type="submit" disabled={submitting} className="flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-bold text-white bg-violet-600 hover:bg-violet-700 rounded-xl disabled:opacity-70">
                    {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Creating...</> : <><Mail className="w-4 h-4" /> Create User</>}
                  </button>
                </div>
              </form>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── Edit Modal ── */}
      <AnimatePresence>
        {isEditModalOpen && userToEdit && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setIsEditModalOpen(false)} className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50" />
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-white rounded-2xl shadow-xl z-50">
              <div className="p-6 border-b border-slate-100 flex items-center justify-between">
                <h2 className="text-lg font-bold text-slate-900">Edit User</h2>
                <button onClick={() => setIsEditModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg"><X className="w-5 h-5" /></button>
              </div>
              <form onSubmit={handleEditSubmit} className="p-6 space-y-4">
                <div><label className={labelClass}>Full Name</label>
                  <input type="text" required value={userToEdit.name} onChange={(e) => setUserToEdit({ ...userToEdit, name: e.target.value })} className={inputClass} /></div>
                <div><label className={labelClass}>Email (read-only)</label>
                  <input type="email" disabled value={userToEdit.email} className={`${inputClass} bg-slate-50 text-slate-500 cursor-not-allowed`} /></div>
                <div><label className={labelClass}>Role</label>
                  <select value={userToEdit.role} onChange={(e) => setUserToEdit({ ...userToEdit, role: e.target.value })} className={inputClass}>
                    <option value="viewer">Viewer</option>
                    <option value="estimator">Estimator</option>
                    <option value="admin">Admin</option>
                  </select></div>
                <div className="pt-2 flex gap-3">
                  <button type="button" onClick={() => setIsEditModalOpen(false)} className="flex-1 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50 rounded-xl border border-slate-200">Cancel</button>
                  <button type="submit" disabled={submitting} className="flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl disabled:opacity-70">
                    {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</> : <><CheckCircle className="w-4 h-4" /> Save Changes</>}
                  </button>
                </div>
              </form>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── Reset Password Modal ── */}
      <AnimatePresence>
        {isResetModalOpen && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setIsResetModalOpen(false)} className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50" />
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-sm bg-white rounded-2xl shadow-xl z-50">
              <div className="p-6 border-b border-slate-100 flex items-center justify-between">
                <h2 className="text-lg font-bold text-slate-900">Reset Password</h2>
                <button onClick={() => setIsResetModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg"><X className="w-5 h-5" /></button>
              </div>
              <form onSubmit={handleResetSubmit} className="p-6 space-y-4">
                <div><label className={labelClass}>New Password</label>
                  <input type="password" required minLength={6} value={newPw} onChange={(e) => setNewPw(e.target.value)} placeholder="Min. 6 characters" className={inputClass} /></div>
                <div className="flex gap-3">
                  <button type="button" onClick={() => setIsResetModalOpen(false)} className="flex-1 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50 rounded-xl border border-slate-200">Cancel</button>
                  <button type="submit" disabled={submitting} className="flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-bold text-white bg-amber-600 hover:bg-amber-700 rounded-xl disabled:opacity-70">
                    {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Resetting...</> : <><Key className="w-4 h-4" /> Reset Password</>}
                  </button>
                </div>
              </form>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <AICopilot />
    </AppShell>
  );
}
