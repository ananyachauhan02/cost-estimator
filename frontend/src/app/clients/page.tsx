"use client";

import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Search, Plus, Users, BarChart3, TrendingUp, DollarSign, X, Loader2, AlertCircle,
} from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import ClientCard from "@/components/ClientCard";
import AICopilot from "@/components/AICopilot";
import { clientsApi, type Client } from "@/lib/api";

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [newClientName, setNewClientName] = useState("");
  const [newClientIndustry, setNewClientIndustry] = useState("Banking");
  const [submitting, setSubmitting] = useState(false);

  // Fetch real clients from backend
  useEffect(() => {
    fetchClients();
  }, []);

  const fetchClients = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await clientsApi.list();
      setClients(data);
    } catch (err: any) {
      setError(err.message || "Failed to load clients");
    } finally {
      setLoading(false);
    }
  };

  const filtered = clients.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.industry.toLowerCase().includes(search.toLowerCase())
  );

  const handleDelete = async (id: string) => {
    try {
      await clientsApi.delete(id);
      setClients((prev) => prev.filter((c) => c.id !== id));
    } catch (err: any) {
      alert(`Failed to delete: ${err.message}`);
    }
  };

  const handleAddClient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClientName.trim()) return;
    setSubmitting(true);
    try {
      const newClient = await clientsApi.create(newClientName, newClientIndustry || "Banking");
      setClients((prev) => [newClient, ...prev]);
      setShowAddModal(false);
      setNewClientName("");
      setNewClientIndustry("Banking");
    } catch (err: any) {
      alert(`Failed to create client: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const statCards = [
    { icon: Users, label: "Total Clients", value: clients.length, bg: "bg-blue-50", text: "text-blue-600" },
    { icon: BarChart3, label: "Total Estimates", value: clients.reduce((s, c) => s + c.estimateCount, 0), bg: "bg-violet-50", text: "text-violet-600" },
    { icon: DollarSign, label: "Active Clients", value: clients.filter((c) => c.estimateCount > 0).length, bg: "bg-emerald-50", text: "text-emerald-600" },
    { icon: TrendingUp, label: "New This Month", value: clients.filter((c) => new Date(c.createdAt) > new Date(Date.now() - 30 * 86400000)).length, bg: "bg-amber-50", text: "text-amber-600" },
  ];

  return (
    <AppShell breadcrumbs={[{ label: "Clients" }]}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Clients</h1>
            <p className="text-slate-500 text-sm mt-1">Manage your clients and their estimates</p>
          </div>
          <motion.button
            onClick={() => setShowAddModal(true)}
            whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-bold text-white rounded-xl shadow-lg shadow-blue-500/25 btn-shine"
            style={{ background: "linear-gradient(135deg, #2563eb, #1d4ed8)" }}
          >
            <Plus className="w-4 h-4" /> Add New Client
          </motion.button>
        </motion.div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {statCards.map((stat, i) => (
            <motion.div key={stat.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
              className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-9 h-9 rounded-xl ${stat.bg} flex items-center justify-center`}>
                  <stat.icon className={`w-4 h-4 ${stat.text}`} />
                </div>
                <p className="text-xs text-slate-500 font-medium">{stat.label}</p>
              </div>
              <p className="text-2xl font-bold text-slate-900">{stat.value}</p>
            </motion.div>
          ))}
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input type="text" placeholder="Search clients by name or industry..."
            value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full max-w-md pl-11 pr-4 py-3 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all shadow-sm"
          />
        </div>

        {/* Error state */}
        {error && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl mb-6">
            <AlertCircle className="w-4 h-4" /> {error}
            <button onClick={fetchClients} className="ml-auto text-xs underline">Retry</button>
          </div>
        )}

        {/* Loading state */}
        {loading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin mr-3" />
            <span className="text-sm">Loading clients from database...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 text-slate-400">
            <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">No clients found</p>
            {search && <p className="text-sm mt-1">Try clearing your search</p>}
          </div>
        ) : (
          <motion.div layout className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {filtered.map((client) => (
              <ClientCard key={client.id} client={client} onDelete={handleDelete} />
            ))}
          </motion.div>
        )}
      </div>

      {/* Add Client Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <motion.div initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-3xl shadow-2xl border border-slate-200 p-8 w-full max-w-md">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-slate-900">Add New Client</h2>
              <button onClick={() => setShowAddModal(false)}>
                <X className="w-5 h-5 text-slate-400 hover:text-slate-600" />
              </button>
            </div>
            <form onSubmit={handleAddClient} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Client Name *</label>
                <input type="text" required value={newClientName} onChange={(e) => setNewClientName(e.target.value)}
                  placeholder="e.g. ABC Bank"
                  className="w-full px-4 py-3 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Sector</label>
                <select value={newClientIndustry} onChange={(e) => setNewClientIndustry(e.target.value)}
                  className="w-full px-4 py-3 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all bg-white">
                  <option value="Banking">Banking & Finance</option>
                  <option value="Insurance">Insurance</option>
                  <option value="Healthcare">Healthcare</option>
                  <option value="Retail">Retail</option>
                  <option value="Technology">Technology</option>
                  <option value="Government">Government</option>
                </select>
              </div>
              <div className="flex gap-3 mt-2">
                <button type="button" onClick={() => setShowAddModal(false)}
                  className="flex-1 py-3 text-sm font-semibold text-slate-700 bg-slate-100 rounded-xl hover:bg-slate-200 transition-colors">
                  Cancel
                </button>
                <motion.button type="submit" disabled={submitting}
                  whileHover={{ scale: submitting ? 1 : 1.01 }} whileTap={{ scale: submitting ? 1 : 0.99 }}
                  className="flex-1 py-3 text-sm font-bold text-white rounded-xl flex items-center justify-center gap-2 disabled:opacity-70"
                  style={{ background: "linear-gradient(135deg, #2563eb, #1d4ed8)" }}>
                  {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Creating...</> : "Create Client"}
                </motion.button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      <AICopilot />
    </AppShell>
  );
}
