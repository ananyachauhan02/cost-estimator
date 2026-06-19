"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Search,
  Bell,
  ChevronRight,
  X,
  CheckCircle,
  AlertCircle,
  Info,
  User,
  LogOut,
  Settings,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { clearToken } from "@/lib/api";

interface TopBarProps {
  breadcrumbs: { label: string; href?: string }[];
}

const NOTIFICATIONS = [
  { id: 1, type: "success", title: "Estimate Generated", desc: "ABC Bank V14 is ready for download.", time: "2m ago" },
  { id: 2, type: "info", title: "GCP Pricing Updated", desc: "GCP pricing cache refreshed for ap-south-1.", time: "1h ago" },
  { id: 3, type: "warning", title: "Draft Auto-Saved", desc: "DEF Bank draft auto-saved at step 3.", time: "2h ago" },
];

export default function TopBar({ breadcrumbs }: TopBarProps) {
  const router = useRouter();
  const [showNotif, setShowNotif] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [user, setUser] = useState<{ name: string; email: string; role: string } | null>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem("businessnext_user");
    if (stored) {
      try { setUser(JSON.parse(stored)); } catch {}
    }
  }, []);

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotif(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    clearToken();
    localStorage.removeItem("businessnext_user");
    router.push("/");
  };

  const initials = user?.name
    ? user.name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)
    : "?";

  return (
    <header className="fixed top-0 left-64 right-0 h-16 bg-white/90 backdrop-blur-md border-b border-slate-200/80 flex items-center px-6 gap-4 z-30">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1 text-sm text-slate-500 flex-1">
        {breadcrumbs.map((crumb, i) => {
          const isLast = i === breadcrumbs.length - 1;
          const textClasses = cn(isLast ? "text-slate-800 font-semibold" : "hover:text-slate-700 cursor-pointer");
          return (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="w-3 h-3 text-slate-300" />}
              {crumb.href ? (
                <Link href={crumb.href} className={textClasses}>
                  {crumb.label}
                </Link>
              ) : (
                <span className={textClasses}>
                  {crumb.label}
                </span>
              )}
            </span>
          );
        })}
      </div>

      {/* Search */}
      <div className="relative w-64">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          placeholder="Search clients, estimates..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-9 pr-4 py-2 text-sm bg-slate-100 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
        />
      </div>

      {/* Notifications */}
      <div className="relative" ref={notifRef}>
        <button
          onClick={() => setShowNotif(!showNotif)}
          className="relative p-2 rounded-xl hover:bg-slate-100 transition-colors"
        >
          <Bell className="w-5 h-5 text-slate-500" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white" />
        </button>

        <AnimatePresence>
          {showNotif && (
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.96 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 top-12 w-80 bg-white rounded-2xl shadow-2xl border border-slate-200 z-50 overflow-hidden"
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
                <p className="text-sm font-semibold text-slate-800">Notifications</p>
                <button onClick={() => setShowNotif(false)}>
                  <X className="w-4 h-4 text-slate-400 hover:text-slate-600" />
                </button>
              </div>
              <div className="divide-y divide-slate-50">
                {NOTIFICATIONS.map((n) => (
                  <div key={n.id} className="flex gap-3 px-4 py-3 hover:bg-slate-50 transition-colors cursor-pointer">
                    {n.type === "success" && <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />}
                    {n.type === "info" && <Info className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />}
                    {n.type === "warning" && <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />}
                    <div className="flex-1">
                      <p className="text-xs font-semibold text-slate-800">{n.title}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{n.desc}</p>
                    </div>
                    <span className="text-xs text-slate-400 whitespace-nowrap">{n.time}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* User Avatar + Dropdown */}
      <div className="relative" ref={userMenuRef}>
        <button
          id="user-profile-button"
          onClick={() => setShowUserMenu(!showUserMenu)}
          className="flex items-center gap-2 cursor-pointer group px-2 py-1.5 rounded-xl hover:bg-slate-100 transition-colors"
        >
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #2563eb, #7c3aed)" }}
          >
            {initials}
          </div>
          <div className="hidden md:block text-left">
            <p className="text-xs font-semibold text-slate-800 leading-tight">{user?.name || "User"}</p>
            <p className="text-xs text-slate-500 leading-tight capitalize">{user?.role || "—"}</p>
          </div>
          <ChevronDown className={cn("w-3.5 h-3.5 text-slate-400 transition-transform duration-200", showUserMenu && "rotate-180")} />
        </button>

        <AnimatePresence>
          {showUserMenu && (
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.96 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 top-13 mt-1 w-56 bg-white rounded-2xl shadow-2xl border border-slate-200 z-50 overflow-hidden"
            >
              {/* User info header */}
              <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
                <div className="flex items-center gap-3">
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold text-white flex-shrink-0"
                    style={{ background: "linear-gradient(135deg, #2563eb, #7c3aed)" }}
                  >
                    {initials}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-800 truncate">{user?.name || "User"}</p>
                    <p className="text-xs text-slate-500 truncate">{user?.email || ""}</p>
                  </div>
                </div>
              </div>

              {/* Menu items */}
              <div className="py-1.5">
                <Link href="/profile" onClick={() => setShowUserMenu(false)}>
                  <div
                    id="profile-menu-item"
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 cursor-pointer transition-colors"
                  >
                    <User className="w-4 h-4 text-slate-400" />
                    <span>My Profile</span>
                  </div>
                </Link>
                <Link href="/settings" onClick={() => setShowUserMenu(false)}>
                  <div className="flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 cursor-pointer transition-colors">
                    <Settings className="w-4 h-4 text-slate-400" />
                    <span>Settings</span>
                  </div>
                </Link>
              </div>

              <div className="border-t border-slate-100 py-1.5">
                <button
                  id="logout-button"
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 cursor-pointer transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </header>
  );
}
