"use client";

import { motion } from "framer-motion";
import { useState, useEffect, Suspense } from "react";
import dynamic from "next/dynamic";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Server, Database, HardDrive, Cpu, MemoryStick, Cloud, Box, Layers,
  Download, RefreshCw, ShieldCheck, Loader2, AlertTriangle, CheckCircle2,
} from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import { estimatesApi, type EstimateDetail } from "@/lib/api";

const EChartsReact = dynamic(() => import("echarts-for-react"), { ssr: false });

const CLOUD_ICON: Record<string, typeof Cloud> = {
  aws: Cloud, gcp: Cloud, kubeadm: Box, openshift: Layers,
};
const CLOUD_LABEL: Record<string, string> = {
  aws: "AWS", gcp: "GCP", kubeadm: "Kubeadm", openshift: "OpenShift",
};

interface OnpremDistribution {
  worker_nodes?: { role_key: string; label: string; nodes: number; vcpu_per_node: number; ram_per_node: number }[];
  summary?: { total_worker_nodes: number; total_db_nodes: number };
  onprem_db_sizing?: {
    cloud: string;
    db_type: string;
    db: {
      hosting_model: string; licensing: string; primary_label: string; cluster_info: string;
      os: string; region: string; primary_nodes: number; vcpu_per_node: number; ram_per_node_gb: number;
      instance_type: string; managed_tier_label?: string; amd_preferred: boolean | null;
      amd_available_in_region: boolean | null; amd_selected: boolean | null; selection_note: string;
      total_db_ram_gb_requested: number;
    };
    storage: { primary_san_gb: number; reporting_san_gb: number; object_storage_gb: number };
  };
  cloud?: string;
}

function OnpremResultsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const estimateId = searchParams.get("id");
  const clientId = searchParams.get("clientId");

  const [estimate, setEstimate] = useState<EstimateDetail | null>(null);
  const [loading, setLoading] = useState(!!estimateId);
  const [error, setError] = useState<string | null>(estimateId ? null : "No estimate ID provided.");

  useEffect(() => {
    if (!estimateId) {
      return;
    }
    estimatesApi.get(estimateId)
      .then(setEstimate)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [estimateId]);

  if (loading) {
    return (
      <AppShell breadcrumbs={[{ label: "On-Premise Sizing", href: "/onprem/estimate/new" }, { label: "Results" }]}>
        <div className="flex items-center justify-center py-32">
          <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
        </div>
      </AppShell>
    );
  }

  if (error || !estimate) {
    return (
      <AppShell breadcrumbs={[{ label: "On-Premise Sizing", href: "/onprem/estimate/new" }, { label: "Results" }]}>
        <div className="max-w-2xl mx-auto mt-20 p-6 bg-red-50 border border-red-200 rounded-2xl flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
          <div>
            <p className="font-bold text-red-800">Could not load this estimate</p>
            <p className="text-sm text-red-600 mt-1">{error || "No estimate ID provided."}</p>
          </div>
        </div>
      </AppShell>
    );
  }

  const dist = (estimate.distribution || {}) as OnpremDistribution;
  const dbSizing = dist.onprem_db_sizing;
  const cloud = dbSizing?.cloud || dist.cloud || "aws";
  const CloudIcon = CLOUD_ICON[cloud] || Cloud;
  const workerNodes = dist.worker_nodes || [];
  const summary = dist.summary || { total_worker_nodes: 0, total_db_nodes: 0 };

  const metrics = (estimate.metrics || {}) as Record<string, unknown>;
  const totalVcpus = Number(metrics.total_vcpus_workernode ?? 0);
  const totalRamGb = Number(metrics.total_memory_workernode_gb ?? 0);
  const dataGb = Number(metrics.data_size_gb ?? 0);
  const s3Gb = Number(metrics.s3_size_gb ?? 0);

  // ── Worker node role breakdown (donut) ──────────────────────────────────
  const roleColors = ["#d97706", "#b45309", "#92400e", "#f59e0b", "#fbbf24", "#fcd34d"];
  const workerDonutOption = {
    tooltip: { trigger: "item", backgroundColor: "#1e293b", borderColor: "#334155", textStyle: { color: "#f8fafc" } },
    legend: { orient: "vertical", left: "left", top: "middle", textStyle: { color: "#475569", fontSize: 11 } },
    series: [{
      type: "pie", radius: ["45%", "75%"], center: ["68%", "50%"],
      data: workerNodes.map((r, i) => ({
        value: r.nodes, name: r.label.replace("Worker Nodes Linux/RHEL", "").trim() || r.role_key,
        itemStyle: { color: roleColors[i % roleColors.length] },
      })),
      label: { show: true, formatter: "{c}", fontSize: 11, fontWeight: "bold", color: "#1e293b" },
      labelLine: { show: true, length: 6, length2: 6 },
    }],
  };

  // ── Compute shape: worker vs DB (grouped bar — vCPU & RAM) ──────────────
  const dbVcpuTotal = dbSizing ? dbSizing.db.vcpu_per_node * dbSizing.db.primary_nodes : 0;
  const dbRamTotal = dbSizing ? dbSizing.db.ram_per_node_gb * dbSizing.db.primary_nodes : 0;
  const tierOption = {
    tooltip: { trigger: "axis", backgroundColor: "#1e293b", borderColor: "#334155", textStyle: { color: "#f8fafc" } },
    legend: { data: ["vCPU", "RAM (GB)"], textStyle: { color: "#64748b", fontSize: 12 }, top: 0 },
    grid: { left: "3%", right: "4%", bottom: "3%", top: "45px", containLabel: true },
    xAxis: { type: "category", data: ["Worker Tier", `${dbSizing?.db_type || "Database"} Tier`], axisLine: { lineStyle: { color: "#e2e8f0" } }, axisTick: { show: false }, axisLabel: { color: "#94a3b8", fontSize: 12 } },
    yAxis: { type: "value", axisLabel: { color: "#94a3b8", fontSize: 11 }, splitLine: { lineStyle: { color: "#f1f5f9", type: "dashed" } }, axisLine: { show: false }, axisTick: { show: false } },
    series: [
      { name: "vCPU", type: "bar", barWidth: 28, borderRadius: [6, 6, 0, 0],
        itemStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "#d97706" }, { offset: 1, color: "#fbbf24" }] } },
        data: [totalVcpus, dbVcpuTotal] },
      { name: "RAM (GB)", type: "bar", barWidth: 28, borderRadius: [6, 6, 0, 0],
        itemStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "#0891b2" }, { offset: 1, color: "#67e8f9" }] } },
        data: [totalRamGb, dbRamTotal] },
    ],
  };

  // ── Storage breakdown (horizontal bar) ──────────────────────────────────
  const storage = dbSizing?.storage;
  const storageOption = {
    tooltip: { trigger: "axis", backgroundColor: "#1e293b", borderColor: "#334155", textStyle: { color: "#f8fafc" } },
    grid: { left: "3%", right: "8%", bottom: "3%", top: "10px", containLabel: true },
    xAxis: { type: "value", axisLabel: { color: "#94a3b8", fontSize: 11, formatter: (v: number) => `${v.toLocaleString()} GB` }, splitLine: { lineStyle: { color: "#f1f5f9", type: "dashed" } } },
    yAxis: { type: "category", data: ["Object Storage", "Reporting SAN", "Primary SAN"], axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: "#475569", fontSize: 12, fontWeight: "bold" } },
    series: [{
      type: "bar", barWidth: 22, barCategoryGap: "40%",
      itemStyle: { borderRadius: [0, 6, 6, 0], color: { type: "linear", x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: "#0e7490" }, { offset: 1, color: "#22d3ee" }] } },
      label: { show: true, position: "right", color: "#1e293b", fontSize: 11, fontWeight: "bold", formatter: (p: { value: number }) => `${p.value.toLocaleString()} GB` },
      data: [storage?.object_storage_gb || s3Gb, storage?.reporting_san_gb || dataGb, storage?.primary_san_gb || dataGb],
    }],
  };

  const downloadUrl = estimate.id ? estimatesApi.downloadUrl(estimate.id, "sizing") : "#";

  return (
    <AppShell breadcrumbs={[{ label: "On-Premise Sizing", href: "/onprem/estimate/new" }, { label: estimate.customerName || "Results" }]}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 bg-amber-100 text-amber-700 text-[11px] font-bold rounded-full uppercase tracking-wide">On-Premise</span>
              <span className="px-2.5 py-0.5 bg-slate-100 text-slate-600 text-[11px] font-bold rounded-full flex items-center gap-1">
                <CloudIcon className="w-3 h-3" /> {CLOUD_LABEL[cloud] || cloud}
              </span>
              <span className="px-2.5 py-0.5 bg-slate-100 text-slate-600 text-[11px] font-bold rounded-full">{dbSizing?.db_type || estimate.dbType}</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900">{estimate.customerName}</h1>
            <p className="text-sm text-slate-500">Infrastructure sizing — no cost figures, sizing only</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push(`/onprem/estimate/new?clientId=${clientId ?? ""}&clientName=${estimate.customerName}`)}
              className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors">
              <RefreshCw className="w-4 h-4" /> Recalculate
            </button>
            <a href={downloadUrl}
              className="flex items-center gap-2 px-5 py-2 text-sm font-bold text-white rounded-xl"
              style={{ background: "linear-gradient(135deg, #d97706, #b45309)" }}>
              <Download className="w-4 h-4" /> Download Sizing Workbook
            </a>
          </div>
        </motion.div>

        {/* KPI strip */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            { icon: Server, label: "Worker Nodes", value: summary.total_worker_nodes ?? metrics.workerNodes ?? 0 },
            { icon: Database, label: "Database Nodes", value: summary.total_db_nodes ?? dbSizing?.db.primary_nodes ?? 0 },
            { icon: Cpu, label: "Total vCPUs (Worker)", value: totalVcpus },
            { icon: MemoryStick, label: "Total RAM (Worker, GB)", value: totalRamGb },
          ].map((kpi) => (
            <div key={kpi.label} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4">
              <kpi.icon className="w-4 h-4 text-amber-500 mb-2" />
              <p className="text-2xl font-bold text-slate-900">{Number(kpi.value).toLocaleString()}</p>
              <p className="text-xs text-slate-500 font-medium">{kpi.label}</p>
            </div>
          ))}
        </div>

        {/* Database sizing card */}
        {dbSizing && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Database className="w-4 h-4 text-amber-600" /> {dbSizing.db_type} — Database Sizing
              </h3>
              <span className="px-3 py-1 bg-slate-100 text-slate-700 text-xs font-bold rounded-full">{dbSizing.db.hosting_model}</span>
            </div>
            <div className="grid grid-cols-4 gap-4 mb-4">
              <div className="bg-slate-50 rounded-xl p-3.5">
                <p className="text-[11px] text-slate-500 font-medium">Primary Nodes</p>
                <p className="text-lg font-bold text-slate-900 mt-0.5">{dbSizing.db.primary_nodes}</p>
              </div>
              <div className="bg-slate-50 rounded-xl p-3.5">
                <p className="text-[11px] text-slate-500 font-medium">vCPU / RAM per Node</p>
                <p className="text-lg font-bold text-slate-900 mt-0.5">{dbSizing.db.vcpu_per_node} / {dbSizing.db.ram_per_node_gb} GB</p>
              </div>
              <div className="bg-slate-50 rounded-xl p-3.5">
                <p className="text-[11px] text-slate-500 font-medium">Instance / Tier</p>
                <p className="text-sm font-bold text-slate-900 mt-0.5 truncate" title={dbSizing.db.managed_tier_label || dbSizing.db.instance_type}>
                  {dbSizing.db.managed_tier_label || dbSizing.db.instance_type}
                </p>
              </div>
              <div className="bg-slate-50 rounded-xl p-3.5">
                <p className="text-[11px] text-slate-500 font-medium">Cluster Architecture</p>
                <p className="text-sm font-bold text-slate-900 mt-0.5">{dbSizing.db.cluster_info}</p>
              </div>
            </div>
            <div className="flex items-start gap-2 p-3.5 bg-amber-50 border border-amber-100 rounded-xl mb-3">
              <ShieldCheck className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs font-semibold text-amber-800">{dbSizing.db.licensing}</p>
                <p className="text-[11px] text-amber-700 mt-0.5">{dbSizing.db.selection_note}</p>
              </div>
            </div>
            {dbSizing.db.amd_preferred !== null && (
              <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                {dbSizing.db.amd_selected
                  ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  : <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />}
                AMD EPYC {dbSizing.db.amd_selected ? "selected" : "not available — equivalent alternative used"} for region {dbSizing.db.region}
              </div>
            )}
          </motion.div>
        )}

        {/* Charts row */}
        <div className="grid grid-cols-2 gap-5 mb-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-sm font-bold text-slate-900 mb-1">Worker Node Role Distribution</h3>
            <p className="text-xs text-slate-500 mb-3">Node count by application tier role</p>
            <EChartsReact option={workerDonutOption} style={{ height: 260 }} />
          </div>
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-sm font-bold text-slate-900 mb-1">Compute Shape — Worker vs Database Tier</h3>
            <p className="text-xs text-slate-500 mb-3">Total vCPU and RAM by tier</p>
            <EChartsReact option={tierOption} style={{ height: 260 }} />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-5 mb-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-sm font-bold text-slate-900 mb-1 flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-cyan-600" /> Storage Sizing
            </h3>
            <p className="text-xs text-slate-500 mb-3">Primary SAN, reporting SAN, and object storage requirements</p>
            <EChartsReact option={storageOption} style={{ height: 180 }} />
          </div>
        </div>

        {/* Worker role table */}
        {workerNodes.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50">
              <p className="text-xs font-bold text-slate-700 uppercase tracking-wide">Worker Node Detail</p>
            </div>
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left px-5 py-2.5 text-xs font-semibold text-slate-500">Role</th>
                  <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500">Nodes</th>
                  <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500">vCPU / Node</th>
                  <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500">RAM / Node (GB)</th>
                </tr>
              </thead>
              <tbody>
                {workerNodes.map((r) => (
                  <tr key={r.role_key} className="border-b border-slate-50 last:border-0">
                    <td className="px-5 py-2.5 text-sm text-slate-700">{r.label}</td>
                    <td className="px-4 py-2.5 text-sm text-right font-semibold text-slate-900">{r.nodes}</td>
                    <td className="px-4 py-2.5 text-sm text-right text-slate-600">{r.vcpu_per_node}</td>
                    <td className="px-4 py-2.5 text-sm text-right text-slate-600">{r.ram_per_node}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default function OnpremResultsPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-slate-400">Loading…</div>}>
      <OnpremResultsContent />
    </Suspense>
  );
}
