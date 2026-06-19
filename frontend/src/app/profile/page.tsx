"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  User,
  Mail,
  Shield,
  Key,
  Eye,
  EyeOff,
  CheckCircle,
  AlertCircle,
  Loader2,
  Calendar,
} from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import { usersApi } from "@/lib/api";

export default function ProfilePage() {
  const [user, setUser] = useState<{ id: string; name: string; email: string; role: string; created_at?: string } | null>(null);

  // Password reset state
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [resetSuccess, setResetSuccess] = useState("");
  const [resetError, setResetError] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("businessnext_user");
    if (stored) {
      try { setUser(JSON.parse(stored)); } catch {}
    }
  }, []);

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetError("");
    setResetSuccess("");

    if (newPassword.length < 6) {
      setResetError("Password must be at least 6 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setResetError("Passwords do not match.");
      return;
    }
    if (!user?.id) {
      setResetError("User not found. Please log in again.");
      return;
    }

    setResetLoading(true);
    try {
      await usersApi.resetPassword(user.id, newPassword);
      setResetSuccess("Password updated successfully.");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      setResetError(err.message || "Failed to update password.");
    } finally {
      setResetLoading(false);
    }
  };

  const roleColors: Record<string, string> = {
    admin: "bg-violet-100 text-violet-700 border-violet-200",
    estimator: "bg-blue-100 text-blue-700 border-blue-200",
    viewer: "bg-slate-100 text-slate-600 border-slate-200",
  };

  const roleColor = roleColors[user?.role || "viewer"] ?? roleColors.viewer;

  const initials = user?.name
    ? user.name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)
    : "?";

  return (
    <AppShell breadcrumbs={[{ label: "My Profile" }]}>
      <div className="max-w-2xl mx-auto space-y-6">

        {/* Profile Card */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden"
        >
          {/* Header banner */}
          <div
            className="h-24 w-full"
            style={{ background: "linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)" }}
          />

          <div className="px-8 pb-8 -mt-10">
            {/* Avatar */}
            <div
              className="w-20 h-20 rounded-2xl border-4 border-white shadow-lg flex items-center justify-center text-2xl font-bold text-white mb-4"
              style={{ background: "linear-gradient(135deg, #2563eb, #7c3aed)" }}
            >
              {initials}
            </div>

            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-xl font-bold text-slate-900">{user?.name || "—"}</h1>
                <p className="text-slate-500 text-sm mt-0.5">{user?.email || "—"}</p>
              </div>
              <span className={`mt-1 text-xs font-semibold px-3 py-1 rounded-full border capitalize ${roleColor}`}>
                {user?.role || "—"}
              </span>
            </div>

            {/* Details grid */}
            <div className="mt-6 grid grid-cols-1 gap-4">
              {[
                { icon: User, label: "Full Name", value: user?.name || "—" },
                { icon: Mail, label: "Email Address", value: user?.email || "—" },
                { icon: Shield, label: "Role", value: user?.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : "—" },
                { icon: Calendar, label: "Member Since", value: user?.created_at ? new Date(user.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) : "—" },
              ].map(({ icon: Icon, label, value }) => (
                <div key={label} className="flex items-center gap-4 px-4 py-3 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-4 h-4 text-slate-500" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 font-medium">{label}</p>
                    <p className="text-sm text-slate-800 font-semibold mt-0.5">{value}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Reset Password Card */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="bg-white rounded-2xl border border-slate-200 shadow-sm"
        >
          <div className="px-6 py-5 border-b border-slate-100 flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center">
              <Key className="w-4 h-4 text-blue-600" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-800">Reset Password</h2>
              <p className="text-xs text-slate-400">Choose a strong new password for your account</p>
            </div>
          </div>

          <form onSubmit={handleResetPassword} className="px-6 py-5 space-y-4">
            {/* New Password */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">New Password</label>
              <div className="relative">
                <input
                  id="new-password-input"
                  type={showNew ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Min. 6 characters"
                  className="w-full px-4 py-2.5 pr-10 text-sm border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowNew(!showNew)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">Confirm New Password</label>
              <div className="relative">
                <input
                  id="confirm-password-input"
                  type={showConfirm ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter your new password"
                  className="w-full px-4 py-2.5 pr-10 text-sm border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Feedback messages */}
            {resetSuccess && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 px-4 py-3 rounded-xl"
              >
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                {resetSuccess}
              </motion.div>
            )}
            {resetError && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 px-4 py-3 rounded-xl"
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {resetError}
              </motion.div>
            )}

            <motion.button
              id="reset-password-submit"
              type="submit"
              disabled={resetLoading}
              whileHover={{ scale: resetLoading ? 1 : 1.01 }}
              whileTap={{ scale: resetLoading ? 1 : 0.99 }}
              className="w-full py-2.5 text-sm font-bold text-white rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-70"
              style={{ background: "linear-gradient(135deg, #2563eb, #1d4ed8)" }}
            >
              {resetLoading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Updating...</>
              ) : (
                <><Key className="w-4 h-4" /> Update Password</>
              )}
            </motion.button>
          </form>
        </motion.div>

      </div>
    </AppShell>
  );
}
