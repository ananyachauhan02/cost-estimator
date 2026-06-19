"use client";

import { motion } from "framer-motion";
import dynamic from "next/dynamic";
import Link from "next/link";
import {
  Users, BarChart3, TrendingUp, DollarSign,
  ArrowRight, Clock, CheckCircle, PlusCircle, Activity,
} from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import AICopilot from "@/components/AICopilot";
import { MOCK_CLIENTS, MOCK_STATS, MOCK_RESULTS } from "@/lib/mock-data";
import { formatCurrency } from "@/lib/utils";

const EChartsReact = dynamic(() => import("echarts-for-react"), { ssr: false });

const RECENT_ACTIVITY = [
  { action: "Estimate Generated", client: "ABC Bank", time: "2 hours ago", status: "success" },
  { action: "New Client Added", client: "DEF Corp", time: "5 hours ago", status: "info" },
  { action: "Report Downloaded", client: "XYZ Financial", time: "1 day ago", status: "success" },
  { action: "Draft Auto-Saved", client: "DEF Bank", time: "2 days ago", status: "warning" },
];

export default function DashboardPage() {
  const revenueOption = {
    tooltip: { trigger: "axis", backgroundColor: "#1e293b", borderColor: "#334155", textStyle: { color: "#f8fafc" } },
    grid: { left: 0, right: 0, top: "5px", bottom: "20px", containLabel: true },
    xAxis: { type: "category", data: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"], axisLabel: { color: "#94a3b8", fontSize: 11 }, axisLine: { show: false }, axisTick: { show: false } },
    yAxis: { type: "value", show: false },
    series: [{
      type: "bar", data: [18, 24, 19, 31, 28, 42], barWidth: "50%", borderRadius: [4, 4, 0, 0],
      itemStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "#2563eb" }, { offset: 1, color: "#60a5fa" }] } },
    }],
  };

  return (
    <AppShell breadcrumbs={[{ label: "Dashboard" }]}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-slate-500 text-sm mt-1">Welcome back, John. Here's what's happening today.</p>
        </motion.div>

        {/* Stat cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            { icon: Users, label: "Total Clients", value: MOCK_STATS.totalClients, change: "+2 this month", up: true, color: "blue" },
            { icon: BarChart3, label: "Total Estimates", value: MOCK_STATS.totalEstimates, change: "+8 this month", up: true, color: "violet" },
            { icon: DollarSign, label: "Avg Monthly Cost", value: formatCurrency(MOCK_STATS.avgMonthlyCost), change: "+3.2%", up: true, color: "indigo" },
            { icon: TrendingUp, label: "Total Savings Found", value: formatCurrency(MOCK_STATS.totalSavings), change: "Lifetime", up: false, color: "emerald" },
          ].map((card, i) => (
            <motion.div key={card.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
              className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  card.color === "blue" ? "bg-blue-100" : card.color === "violet" ? "bg-violet-100" :
                  card.color === "indigo" ? "bg-indigo-100" : "bg-emerald-100"}`}>
                  <card.icon className={`w-5 h-5 ${
                    card.color === "blue" ? "text-blue-600" : card.color === "violet" ? "text-violet-600" :
                    card.color === "indigo" ? "text-indigo-600" : "text-emerald-600"}`} />
                </div>
                <span className={`text-xs font-semibold px-2 py-1 rounded-full ${card.up ? "bg-emerald-100 text-emerald-700" : "bg-blue-100 text-blue-700"}`}>
                  {card.change}
                </span>
              </div>
              <p className="text-2xl font-bold text-slate-900">{card.value}</p>
              <p className="text-xs text-slate-500 mt-1">{card.label}</p>
            </motion.div>
          ))}
        </div>

        {/* Middle row */}
        <div className="grid grid-cols-3 gap-5 mb-6">
          {/* Estimates by month */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-900">Estimates Generated</h3>
              <span className="text-xs text-slate-400">Last 6 months</span>
            </div>
            <EChartsReact option={revenueOption} style={{ height: 120 }} />
          </div>

          {/* Quick actions */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-sm font-bold text-slate-900 mb-4">Quick Actions</h3>
            <div className="space-y-2">
              {[
                { icon: PlusCircle, label: "New Estimate", href: "/estimate/new", color: "blue" },
                { icon: Users, label: "Add Client", href: "/clients", color: "violet" },
                { icon: BarChart3, label: "View Reports", href: "/reports", color: "emerald" },
              ].map((action) => (
                <Link key={action.label} href={action.href}>
                  <motion.div whileHover={{ x: 3 }}
                    className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 transition-colors cursor-pointer group border border-transparent hover:border-slate-200">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      action.color === "blue" ? "bg-blue-100" : action.color === "violet" ? "bg-violet-100" : "bg-emerald-100"}`}>
                      <action.icon className={`w-4 h-4 ${
                        action.color === "blue" ? "text-blue-600" : action.color === "violet" ? "text-violet-600" : "text-emerald-600"}`} />
                    </div>
                    <span className="text-sm font-medium text-slate-700 group-hover:text-slate-900">{action.label}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
                  </motion.div>
                </Link>
              ))}
            </div>
          </div>

          {/* Latest estimate */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-sm font-bold text-slate-900 mb-4">Latest Estimate</h3>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white text-sm font-bold bg-gradient-to-br from-blue-500 to-blue-700">AB</div>
              <div>
                <p className="text-sm font-bold text-slate-800">ABC Bank</p>
                <p className="text-xs text-slate-500">V14 · SaaS · Jun 2026</p>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-xs"><span className="text-slate-500">Monthly Cost</span><span className="font-bold text-blue-600">{formatCurrency(MOCK_RESULTS.awsMonthlyCost)}</span></div>
              <div className="flex justify-between text-xs"><span className="text-slate-500">Annual Cost</span><span className="font-bold">{formatCurrency(MOCK_RESULTS.awsAnnualCost)}</span></div>
              <div className="flex justify-between text-xs"><span className="text-slate-500">5Y TCO</span><span className="font-bold">{formatCurrency(MOCK_RESULTS.aws5YearTCO)}</span></div>
            </div>
            <Link href="/results">
              <button className="w-full mt-4 py-2 text-xs font-bold text-blue-600 bg-blue-50 rounded-xl hover:bg-blue-100 transition-colors">
                View Results →
              </button>
            </Link>
          </div>
        </div>

        {/* Bottom row */}
        <div className="grid grid-cols-5 gap-5">
          {/* Recent clients */}
          <div className="col-span-3 bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-900">Recent Clients</h3>
              <Link href="/clients" className="text-xs text-blue-600 font-medium hover:underline">View all →</Link>
            </div>
            <div className="space-y-3">
              {MOCK_CLIENTS.slice(0, 4).map((client) => (
                <div key={client.id} className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 transition-colors">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-white text-xs font-bold bg-gradient-to-br ${client.color}`}>
                    {client.logo}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-800 truncate">{client.name}</p>
                    <p className="text-xs text-slate-500">{client.industry}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-bold text-slate-700">{client.estimateCount} estimates</p>
                    <p className="text-xs text-slate-400">{client.lastActivity}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent activity */}
          <div className="col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-4 h-4 text-slate-500" />
              <h3 className="text-sm font-bold text-slate-900">Recent Activity</h3>
            </div>
            <div className="space-y-3">
              {RECENT_ACTIVITY.map((activity, i) => (
                <div key={i} className="flex gap-3">
                  <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                    activity.status === "success" ? "bg-emerald-400" :
                    activity.status === "warning" ? "bg-amber-400" : "bg-blue-400"}`} />
                  <div>
                    <p className="text-xs font-semibold text-slate-800">{activity.action}</p>
                    <p className="text-xs text-slate-500">{activity.client}</p>
                    <p className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                      <Clock className="w-2.5 h-2.5" />{activity.time}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <AICopilot />
    </AppShell>
  );
}
