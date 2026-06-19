"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { BarChart3, ArrowRight, TrendingDown, TrendingUp, Minus } from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import AICopilot from "@/components/AICopilot";
import { COMPARISON_SCENARIOS } from "@/lib/mock-data";
import { formatCurrency } from "@/lib/utils";

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState<"scenarios" | "drafts">("scenarios");

  return (
    <AppShell breadcrumbs={[{ label: "Reports" }]}>
      <div className="max-w-7xl mx-auto">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">Reports & Comparisons</h1>
          <p className="text-slate-500 text-sm mt-1">Compare scenarios and analyze estimate trends</p>
        </motion.div>

        {/* Tab */}
        <div className="flex gap-1 bg-white border border-slate-200 rounded-2xl p-1.5 mb-6 w-fit shadow-sm">
          {[{ key: "scenarios", label: "Cost Comparisons" }, { key: "drafts", label: "Saved Drafts" }].map((tab) => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key as "scenarios" | "drafts")}
              className={`px-5 py-2 text-sm font-semibold rounded-xl transition-all ${activeTab === tab.key ? "text-white" : "text-slate-500 hover:text-slate-700"}`}
              style={activeTab === tab.key ? { background: "linear-gradient(135deg, #2563eb, #1d4ed8)" } : {}}>
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "scenarios" && (
          <div>
            <div className="grid grid-cols-3 gap-5">
              {COMPARISON_SCENARIOS.map((scenario, i) => (
                <motion.div key={scenario.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
                  className={`bg-white rounded-2xl border-2 shadow-sm p-6 ${scenario.id === "base" ? "border-blue-500" : "border-slate-200"}`}>
                  {scenario.id === "base" && (
                    <span className="px-2.5 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded-full mb-3 inline-block">Current</span>
                  )}
                  <h3 className="text-base font-bold text-slate-900 mb-1">{scenario.name}</h3>
                  <p className="text-sm text-slate-500 mb-5">{scenario.description}</p>
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Users</span>
                      <span className="font-bold text-slate-800">{scenario.users.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Deployment</span>
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${scenario.deployment === "SaaS" ? "bg-violet-100 text-violet-700" : "bg-amber-100 text-amber-700"}`}>
                        {scenario.deployment}
                      </span>
                    </div>
                    <div className="border-t border-slate-100 pt-3">
                      <div className="flex justify-between">
                        <span className="text-xs text-slate-500">AWS Monthly</span>
                        <span className="text-lg font-bold text-blue-600">{formatCurrency(scenario.awsCost)}</span>
                      </div>
                      <div className="flex justify-between mt-1">
                        <span className="text-xs text-slate-500">GCP Monthly</span>
                        <span className="text-lg font-bold text-violet-600">{formatCurrency(scenario.gcpCost)}</span>
                      </div>
                    </div>
                    {i > 0 && (
                      <div className={`flex items-center gap-1.5 text-xs font-semibold pt-2 ${
                        scenario.awsCost > COMPARISON_SCENARIOS[0].awsCost ? "text-red-500" : "text-emerald-600"}`}>
                        {scenario.awsCost > COMPARISON_SCENARIOS[0].awsCost ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        {scenario.awsCost > COMPARISON_SCENARIOS[0].awsCost ? "+" : "-"}
                        {formatCurrency(Math.abs(scenario.awsCost - COMPARISON_SCENARIOS[0].awsCost))} vs Current
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Comparison table */}
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
              className="mt-6 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100">
                <h3 className="text-sm font-bold text-slate-900">Side-by-Side Comparison</h3>
              </div>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-100">
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase">Metric</th>
                    {COMPARISON_SCENARIOS.map((s) => (
                      <th key={s.id} className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase">{s.name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {[
                    { label: "Users", key: "users", format: (v: number) => v.toLocaleString() },
                    { label: "AWS Monthly", key: "awsCost", format: formatCurrency },
                    { label: "GCP Monthly", key: "gcpCost", format: formatCurrency },
                    { label: "AWS Annual", key: "awsCost", format: (v: number) => formatCurrency(v * 12) },
                    { label: "AWS 5Y TCO", key: "awsCost", format: (v: number) => formatCurrency(v * 60) },
                  ].map((row) => (
                    <tr key={row.label} className="table-row-hover">
                      <td className="px-5 py-3.5 text-sm font-medium text-slate-700">{row.label}</td>
                      {COMPARISON_SCENARIOS.map((s) => (
                        <td key={s.id} className="px-5 py-3.5 text-sm font-bold text-slate-900">
                          {row.format((s as unknown as Record<string, number>)[row.key])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </motion.div>
          </div>
        )}

        {activeTab === "drafts" && (
          <div className="grid grid-cols-3 gap-5">
            {[
              { name: "DEF Bank – Draft", client: "DEF Bank", step: 3, saved: "2 hours ago", deployment: "SaaS", users: 8000 },
              { name: "GHI Corp – On-Prem", client: "GHI Corporation", step: 2, saved: "1 day ago", deployment: "On-Premise", users: 15000 },
            ].map((draft, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
                className="bg-white rounded-2xl border border-dashed border-amber-300 shadow-sm p-5">
                <div className="flex items-center gap-2 mb-3">
                  <span className="px-2.5 py-1 bg-amber-100 text-amber-700 text-xs font-bold rounded-full">Draft</span>
                  <span className="text-xs text-slate-400">Step {draft.step}/6</span>
                </div>
                <h3 className="text-base font-bold text-slate-900 mb-1">{draft.name}</h3>
                <p className="text-sm text-slate-500 mb-4">{draft.client} · {draft.users.toLocaleString()} users</p>
                <div className="w-full bg-slate-200 rounded-full h-1.5 mb-4">
                  <div className="h-full rounded-full bg-amber-400" style={{ width: `${(draft.step / 6) * 100}%` }} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Saved {draft.saved}</span>
                  <button className="flex items-center gap-1 text-xs font-bold text-blue-600 hover:underline">
                    Continue <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
      <AICopilot />
    </AppShell>
  );
}
