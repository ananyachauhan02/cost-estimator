"use client";

import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft, Download, Copy, Upload, FileText, FileSpreadsheet,
  ChevronUp, ChevronDown, CheckCircle, Eye, ChevronLeft,
  ChevronRight, PlusCircle, Loader2, AlertCircle, Trash2,
} from "lucide-react";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import AICopilot from "@/components/AICopilot";
import { clientsApi, estimatesApi, type Client, type Estimate } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

type SortField = "version" | "name" | "deployment" | "date" | "awsMonthlyCost";
type SortDir = "asc" | "desc";

export default function EstimateHistoryPage() {
  const params = useParams();
  const clientId = params.clientId as string;
  const router = useRouter();

  const [client, setClient] = useState<Client | null>(null);
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sortField, setSortField] = useState<SortField>("version");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(1);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const pageSize = 5;

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        // Fetch estimates (primary — must succeed)
        const estimateData = await estimatesApi.listByClient(clientId);
        setEstimates(estimateData);
      } catch (err: any) {
        setError(err.message || "Failed to load estimates");
      } finally {
        setLoading(false);
      }
      // Fetch client info separately (secondary — failure is non-fatal)
      try {
        const clientData = await clientsApi.get(clientId);
        setClient(clientData);
      } catch {
        // Use a placeholder if client fetch fails
        setClient({ id: clientId, name: `Client #${clientId}`, industry: "—", createdAt: "", estimateCount: 0, lastActivity: "—", status: "active", logo: clientId[0]?.toUpperCase() ?? "C", color: "from-blue-500 to-blue-700" });
      }
    };
    load();
  }, [clientId]);

  const handleSort = (field: SortField) => {
    if (field === sortField) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortField(field); setSortDir("asc"); }
  };

  const sorted = [...estimates].sort((a, b) => {
    const mult = sortDir === "asc" ? 1 : -1;
    const av = a[sortField as keyof Estimate] ?? "";
    const bv = b[sortField as keyof Estimate] ?? "";
    if (av < bv) return -mult;
    if (av > bv) return mult;
    return 0;
  });

  const paginated = sorted.slice((page - 1) * pageSize, page * pageSize);
  const totalPages = Math.ceil(sorted.length / pageSize);

  const SortIcon = ({ field }: { field: SortField }) =>
    sortField === field
      ? sortDir === "asc" ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
      : <div className="w-3 h-3 opacity-0 group-hover:opacity-40"><ChevronDown className="w-3 h-3" /></div>;

  const handleLoad = (id: string) => {
    router.push(`/results?id=${id}&clientId=${clientId}`);
  };

  const handleDownloadPdf = (id: string) => {
    const url = estimatesApi.pdfUrl(id);
    const token = localStorage.getItem("businessnext_token");
    window.open(`${url}?token=${token}`, "_blank");
  };

  const handleDownloadAll = (id: string) => {
    const url = estimatesApi.downloadAllUrl(id);
    const token = localStorage.getItem("businessnext_token");
    window.open(`${url}?token=${token}`, "_blank");
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this estimate? This cannot be undone.")) return;
    try {
      await estimatesApi.delete(id);
      setEstimates((prev) => prev.filter((e) => e.id !== id));
    } catch (err: any) {
      alert(`Failed to delete: ${err.message}`);
    }
  };

  const handleDownload = (estimateId: string, type: "sizing" | "pricing") => {
    const url = estimatesApi.downloadUrl(estimateId, type);
    const token = localStorage.getItem("businessnext_token");
    // Open in new tab — browser will handle the download
    // We add the token as a query param since browser navigations don't support custom headers
    window.open(`${url}?token=${token}`, "_blank");
  };

  if (loading) {
    return (
      <AppShell breadcrumbs={[{ label: "Clients", href: "/clients" }, { label: "Loading..." }]}>
        <div className="flex items-center justify-center py-32 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mr-3" />
          <span className="text-sm">Loading estimates...</span>
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell breadcrumbs={[{ label: "Clients", href: "/clients" }, { label: "Error" }]}>
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl mt-4">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      </AppShell>
    );
  }

  const latestEstimate = sorted[0];
  const latestMonthly = latestEstimate?.awsMonthlyCost ?? 0;
  const latestVersion = latestEstimate?.version ?? "—";

  return (
    <AppShell breadcrumbs={[{ label: "Clients", href: "/clients" }, { label: client?.name ?? "" }, { label: "Estimate History" }]}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-4">
            <Link href="/clients">
              <button className="p-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 transition-colors">
                <ArrowLeft className="w-4 h-4 text-slate-500" />
              </button>
            </Link>
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-sm bg-gradient-to-br ${client?.color ?? "from-blue-500 to-blue-700"}`}>
                {client?.logo}
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-900">{client?.name}</h1>
                <p className="text-slate-500 text-sm">Estimate History</p>
              </div>
            </div>
          </div>
          <Link href={`/estimate/new?clientId=${clientId}&clientName=${encodeURIComponent(client?.name || "")}`}>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              className="flex items-center gap-2 px-5 py-2.5 text-sm font-bold text-white rounded-xl shadow-lg shadow-blue-500/25 btn-shine"
              style={{ background: "linear-gradient(135deg, #2563eb, #1d4ed8)" }}>
              <PlusCircle className="w-4 h-4" /> New Estimate
            </motion.button>
          </Link>
        </motion.div>

        {/* Summary bar */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="grid grid-cols-4 gap-4 mb-6">
          {[
            { label: "Total Estimates", value: estimates.length },
            { label: "Latest Version", value: latestVersion },
            { label: "Latest Monthly Cost", value: latestMonthly > 0 ? formatCurrency(latestMonthly) : "—", highlight: true },
            { label: "Sector", value: client?.industry ?? "—" },
          ].map((item) => (
            <div key={item.label} className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
              <p className="text-xs text-slate-500 mb-1">{item.label}</p>
              <p className={`text-lg font-bold ${item.highlight ? "text-blue-600" : "text-slate-900"}`}>{item.value}</p>
            </div>
          ))}
        </motion.div>

        {/* Empty state */}
        {estimates.length === 0 ? (
          <div className="text-center py-20 text-slate-400 bg-white rounded-2xl border border-slate-200">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">No estimates yet</p>
            <p className="text-sm mt-1">Create a new estimate to get started.</p>
          </div>
        ) : (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-100">
                    {[
                      { label: "Version", field: "version" as SortField },
                      { label: "Estimate Name", field: "name" as SortField },
                      { label: "Deployment", field: "deployment" as SortField },
                      { label: "Date", field: "date" as SortField },
                      { label: "AWS Monthly", field: "awsMonthlyCost" as SortField },
                      { label: "GCP Monthly", field: null },
                      { label: "Status", field: null },
                      { label: "Actions", field: null },
                    ].map((col) => (
                      <th key={col.label} onClick={() => col.field && handleSort(col.field)}
                        className={`text-left px-5 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider select-none group ${col.field ? "cursor-pointer hover:text-slate-700" : ""}`}>
                        <span className="flex items-center gap-1">
                          {col.label}
                          {col.field && <SortIcon field={col.field} />}
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {paginated.map((est, i) => (
                    <motion.tr key={est.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
                      className="table-row-hover transition-colors">
                      <td className="px-5 py-4">
                        <span className="px-2.5 py-1 bg-blue-50 text-blue-700 text-xs font-bold rounded-lg">{est.version}</span>
                      </td>
                      <td className="px-5 py-4 text-sm font-medium text-slate-800">
                        <div>
                          {est.name}
                          {(est as any).notes && (
                            <p className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-1">
                              <svg className="w-3 h-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a2 2 0 012-2z" /></svg>
                              {(est as any).notes}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${est.deployment === "SaaS" ? "bg-violet-100 text-violet-700" : "bg-amber-100 text-amber-700"}`}>
                          {est.deployment}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-sm text-slate-500">{est.date}</td>
                      <td className="px-5 py-4 text-sm font-bold text-slate-900">{formatCurrency(est.awsMonthlyCost)}</td>
                      <td className="px-5 py-4 text-sm text-slate-600">{formatCurrency(est.gcpMonthlyCost)}</td>
                      <td className="px-5 py-4">
                        <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-700">
                          <CheckCircle className="w-3.5 h-3.5" /> {est.status}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-1">
                          <Link href={`/results?estimateId=${est.id}&clientId=${clientId}`}>
                            <button title="View Results" className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                              <Eye className="w-4 h-4" />
                            </button>
                          </Link>
                          <button title="Load Estimate" onClick={() => handleLoad(est.id)}
                            className="p-1.5 text-slate-400 hover:text-violet-600 hover:bg-violet-50 rounded-lg transition-colors">
                            {loadingId === est.id
                              ? <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }} className="w-4 h-4 border-2 border-violet-300 border-t-violet-600 rounded-full" />
                              : <Upload className="w-4 h-4" />}
                          </button>
                          <button title="Download PDF Report" onClick={() => handleDownloadPdf(est.id)}
                            className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors">
                            <FileSpreadsheet className="w-4 h-4" />
                          </button>
                          <button title="Download All Reports (.zip)" onClick={() => handleDownloadAll(est.id)}
                            className="p-1.5 text-slate-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-colors">
                            <Download className="w-4 h-4" />
                          </button>
                          <button title="Delete Estimate" onClick={() => handleDelete(est.id)}
                            className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-5 py-4 border-t border-slate-100">
                <p className="text-xs text-slate-500">
                  Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, sorted.length)} of {sorted.length} estimates
                </p>
                <div className="flex items-center gap-2">
                  <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                    className="p-1.5 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50 transition-colors">
                    <ChevronLeft className="w-4 h-4 text-slate-500" />
                  </button>
                  <span className="text-xs font-medium text-slate-600 px-2">{page} / {totalPages}</span>
                  <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                    className="p-1.5 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50 transition-colors">
                    <ChevronRight className="w-4 h-4 text-slate-500" />
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </div>
      <AICopilot />
    </AppShell>
  );
}
