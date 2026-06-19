"use client";

import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import {
  Bot, Sparkles, TrendingDown, BarChart3, Globe, Zap,
  DollarSign, Server, Database, ChevronRight, RefreshCw,
  Users, FileText, AlertCircle, CheckCircle,
} from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import AICopilot, { openCopilotWithPrompt, openCopilot } from "@/components/AICopilot";
import { getToken } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────
interface EstimateSummary {
  id: string;
  customerName: string;
  version: string;
  awsMonthlyCost: number;
  gcpMonthlyCost: number;
  aws5YearTCO: number;
  clientMode: string;
  dbType: string;
  generatedAt: string;
  cloudProviders: string[];
}

interface StatCard {
  label: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
  color: string;
}

function fmtUSD(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}

export default function AIAssistantPage() {
  const [estimates, setEstimates]   = useState<EstimateSummary[]>([]);
  const [loading, setLoading]       = useState(true);
  const [copilotOpen, setCopilotOpen] = useState(false);

  useEffect(() => {
    const token = getToken();
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    fetch(`${apiBase}/api/all-estimates`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.ok ? r.json() : [])
      .then((data: EstimateSummary[]) => setEstimates(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Derived stats
  const totalMonthly   = estimates.reduce((s, e) => s + (e.awsMonthlyCost || 0), 0);
  const totalTCO       = estimates.reduce((s, e) => s + (e.aws5YearTCO || 0), 0);
  const avgMonthly     = estimates.length ? totalMonthly / estimates.length : 0;
  const gcpSavingsTotal = estimates.reduce((s, e) => s + Math.max(0, (e.awsMonthlyCost || 0) - (e.gcpMonthlyCost || 0)), 0);

  const stats: StatCard[] = [
    {
      label: "Total Estimates",
      value: `${estimates.length}`,
      sub:   "across all clients",
      icon:  <FileText className="w-5 h-5" />,
      color: "from-blue-500 to-blue-600",
    },
    {
      label: "Combined Monthly (AWS)",
      value: fmtUSD(totalMonthly),
      sub:   `avg ${fmtUSD(avgMonthly)}/estimate`,
      icon:  <DollarSign className="w-5 h-5" />,
      color: "from-violet-500 to-violet-600",
    },
    {
      label: "Total 5-Year TCO",
      value: fmtUSD(totalTCO),
      sub:   "across all estimates",
      icon:  <TrendingDown className="w-5 h-5" />,
      color: "from-emerald-500 to-emerald-600",
    },
    {
      label: "Potential GCP Savings",
      value: fmtUSD(gcpSavingsTotal),
      sub:   "if migrating to GCP",
      icon:  <Zap className="w-5 h-5" />,
      color: "from-amber-500 to-orange-500",
    },
  ];

  const QUICK_PROMPTS = [
    { icon: <BarChart3 className="w-4 h-4" />, label: "Which estimate has the highest monthly cost?", color: "blue" },
    { icon: <Globe className="w-4 h-4" />,     label: "Compare AWS vs GCP across all estimates",     color: "violet" },
    { icon: <TrendingDown className="w-4 h-4" />, label: "Top 3 cost optimization opportunities",    color: "emerald" },
    { icon: <Server className="w-4 h-4" />,    label: "Which workloads are over-provisioned?",       color: "amber" },
    { icon: <Database className="w-4 h-4" />,  label: "Database cost breakdown across clients",      color: "rose" },
    { icon: <Users className="w-4 h-4" />,     label: "What is the average cost per named user?",   color: "indigo" },
  ];

  const colorMap: Record<string, string> = {
    blue:   "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100",
    violet: "bg-violet-50 text-violet-700 border-violet-200 hover:bg-violet-100",
    emerald:"bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100",
    amber:  "bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100",
    rose:   "bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100",
    indigo: "bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100",
  };

  const openWithPrompt = (prompt: string) => {
    openCopilotWithPrompt(prompt);
  };

  return (
    <AppShell breadcrumbs={[{ label: "AI Assistant" }]}>
      <div className="max-w-5xl mx-auto space-y-7">

        {/* ── Hero ──────────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className="relative overflow-hidden rounded-3xl p-8"
          style={{ background: "linear-gradient(135deg, #0f1729 0%, #1e1b4b 50%, #1a2540 100%)" }}
        >
          <div className="absolute inset-0 opacity-20"
            style={{ backgroundImage: "radial-gradient(circle at 70% 50%, #7c3aed 0%, transparent 60%)" }} />
          <div className="relative flex items-center gap-6">
            <motion.div
              animate={{ rotate: [0, 5, -5, 0] }} transition={{ duration: 4, repeat: Infinity }}
              className="w-16 h-16 rounded-2xl flex items-center justify-center flex-shrink-0"
              style={{ background: "linear-gradient(135deg, #2563eb, #7c3aed)" }}
            >
              <Sparkles className="w-8 h-8 text-white" />
            </motion.div>
            <div>
              <h1 className="text-2xl font-bold text-white">AI Cost Copilot</h1>
              <p className="text-slate-400 text-sm mt-1 max-w-xl">
                Your intelligent cloud cost advisor — powered by Groq LLaMA 3.3. Ask anything about
                estimates, compare AWS vs GCP, identify savings, or optimize infrastructure sizing.
              </p>
              <div className="flex items-center gap-3 mt-3">
                <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  {loading ? "Loading estimates…" : `${estimates.length} estimates loaded`}
                </span>
                <span className="text-slate-600">·</span>
                <span className="text-xs text-slate-400">Groq LLaMA 3.3 70B</span>
              </div>
            </div>
            <motion.button
              onClick={() => openCopilot()}
              whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
              className="ml-auto flex items-center gap-2 px-5 py-3 text-sm font-bold text-white rounded-xl flex-shrink-0"
              style={{ background: "linear-gradient(135deg, #2563eb, #7c3aed)" }}
            >
              <Bot className="w-4 h-4" /> Open Copilot
            </motion.button>
          </div>
        </motion.div>

        {/* ── Stats ────────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-4 gap-4">
          {stats.map((s, i) => (
            <motion.div key={s.label}
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * i }}
              className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm"
            >
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center mb-3 text-white bg-gradient-to-br ${s.color}`}>
                {s.icon}
              </div>
              <p className="text-xl font-bold text-slate-900">{loading ? "—" : s.value}</p>
              <p className="text-xs font-semibold text-slate-600 mt-0.5">{s.label}</p>
              <p className="text-[10px] text-slate-400 mt-0.5">{s.sub}</p>
            </motion.div>
          ))}
        </div>

        {/* ── Quick Questions ───────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6"
        >
          <div className="flex items-center gap-2 mb-4">
            <Bot className="w-4 h-4 text-violet-600" />
            <h2 className="text-sm font-bold text-slate-900">Ask the Copilot</h2>
            <span className="text-xs text-slate-400">— click any question to start a conversation</span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {QUICK_PROMPTS.map((p, i) => (
              <motion.button key={i}
                whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
                onClick={() => openWithPrompt(p.label)}
                className={`flex items-center gap-3 p-4 rounded-xl border text-left transition-all ${colorMap[p.color]}`}
              >
                <span className="flex-shrink-0">{p.icon}</span>
                <span className="text-sm font-medium">{p.label}</span>
                <ChevronRight className="w-3.5 h-3.5 ml-auto flex-shrink-0 opacity-60" />
              </motion.button>
            ))}
          </div>
        </motion.div>

        {/* ── Estimates overview table ─────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
          className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden"
        >
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-bold text-slate-900">Estimates in Context</h2>
            </div>
            <span className="text-xs text-slate-400">The copilot can answer questions about all of these</span>
          </div>
          {loading ? (
            <div className="py-12 text-center text-sm text-slate-400">Loading estimates…</div>
          ) : estimates.length === 0 ? (
            <div className="py-12 text-center text-sm text-slate-400">
              No estimates found. Create one to get started.
            </div>
          ) : (
            <div className="divide-y divide-slate-50">
              {estimates.slice(0, 8).map((e, i) => (
                <div key={e.id} className="flex items-center gap-4 px-6 py-3.5 hover:bg-slate-50 transition-colors">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                    style={{ background: "linear-gradient(135deg, #2563eb, #7c3aed)" }}>
                    {String(i + 1).padStart(2, "0")}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-900 truncate">{e.customerName}</p>
                    <p className="text-xs text-slate-400">{e.version} · {e.generatedAt}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-sm font-bold text-slate-800">{fmtUSD(e.awsMonthlyCost)}<span className="text-xs text-slate-400 font-normal">/mo</span></p>
                    <p className="text-[10px] text-slate-400">AWS · {e.clientMode === "saas" ? "SaaS" : "On-Prem"}</p>
                  </div>
                  <div className={`px-2 py-0.5 rounded-full text-[10px] font-semibold flex-shrink-0 ${
                    e.awsMonthlyCost > e.gcpMonthlyCost
                      ? "bg-amber-50 text-amber-700"
                      : "bg-emerald-50 text-emerald-700"
                  }`}>
                    {e.awsMonthlyCost > e.gcpMonthlyCost ? "GCP cheaper" : "AWS cheaper"}
                  </div>
                </div>
              ))}
              {estimates.length > 8 && (
                <div className="px-6 py-3 text-xs text-slate-400 text-center">
                  +{estimates.length - 8} more estimates available in the copilot context
                </div>
              )}
            </div>
          )}
        </motion.div>

      </div>

      {/* Floating draggable copilot — always present */}
      <AICopilot />
    </AppShell>
  );
}
