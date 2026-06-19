"use client";

import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import {
  DollarSign,
  Globe,
  Database,
  RefreshCw,
  Save,
  CheckCircle,
  Wifi,
  WifiOff,
  Lock,
  ShieldAlert,
  Info,
  Loader2,
  AlertCircle,
} from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import AICopilot from "@/components/AICopilot";
import { getPlatformSettings, savePlatformSettings } from "@/lib/platformSettings";
import { getToken } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────
interface RegionEntry {
  id: string;
  label: string;
  multiplier: number;
  saved_at?: string;
}

interface PricingCache {
  meta?: { saved_at?: string; pricing_date?: string };
  aws?: {
    live_regions?: string[];
    saved_regions?: Record<string, { label: string; multiplier: number; saved_at: string }>;
  };
  gcp?: {
    live_regions?: string[];
    saved_regions?: Record<string, { label: string; multiplier: number; saved_at: string }>;
  };
  api_status?: {
    aws: { live_api_configured: boolean; source: string; note: string };
    gcp: { live_api_configured: boolean; source: string; note: string };
  };
}

// ── All AWS regions (from aws_machine_catalog.py) ─────────────────────────────
const ALL_AWS_LIVE = [
  { id: "us-east-1",      label: "US East (N. Virginia)" },
  { id: "us-east-2",      label: "US East (Ohio)" },
  { id: "us-west-2",      label: "US West (Oregon)" },
  { id: "eu-west-1",      label: "Europe (Ireland)" },
  { id: "eu-central-1",   label: "Europe (Frankfurt)" },
  { id: "ap-south-1",     label: "Asia Pacific (Mumbai)" },
  { id: "ap-southeast-1", label: "Asia Pacific (Singapore)" },
  { id: "ap-northeast-1", label: "Asia Pacific (Tokyo)" },
];

// ── All GCP regions (from gcp_pricer.py) ──────────────────────────────────────
const ALL_GCP_LIVE = [
  { id: "us-central1",    label: "US Central (Iowa)" },
  { id: "us-east1",       label: "US East (South Carolina)" },
  { id: "us-east4",       label: "US East (N. Virginia)" },
  { id: "us-west1",       label: "US West (Oregon)" },
  { id: "europe-west1",   label: "Europe (Belgium)" },
  { id: "europe-west4",   label: "Europe (Netherlands)" },
  { id: "asia-south1",    label: "Asia Pacific (Mumbai)" },
  { id: "asia-southeast1",label: "Asia Pacific (Singapore)" },
  { id: "asia-northeast1",label: "Asia Pacific (Tokyo)" },
];

function formatDate(iso?: string) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric", month: "short", day: "numeric",
  });
}

function RegionCard({ region, type, apiLive }: { region: RegionEntry; type: "live" | "saved"; apiLive: boolean }) {
  // A region marked as "live" is only truly live if the cloud API is configured
  const isActuallyLive = type === "live" && apiLive;
  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-xl border ${
        isActuallyLive
          ? "border-emerald-200 bg-emerald-50"
          : type === "live"
          ? "border-amber-200 bg-amber-50"
          : "border-slate-200 bg-slate-50"
      }`}
    >
      <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
        isActuallyLive ? "bg-emerald-500 animate-pulse" : "bg-amber-400"
      }`} />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-mono font-semibold text-slate-700 truncate">{region.id}</p>
        <p className="text-xs text-slate-500 truncate">{region.label}</p>
        {type === "saved" && region.saved_at && (
          <p className="text-xs text-amber-600 mt-0.5">Saved: {formatDate(region.saved_at)}</p>
        )}
        {type === "live" && (
          <p className={`text-xs mt-0.5 ${
            isActuallyLive ? "text-emerald-600" : "text-amber-600"
          }`}>
            {isActuallyLive ? "Live API pricing" : "Estimated (API not configured)"}
          </p>
        )}
      </div>
      {type !== "live" && (
        <span className="text-xs text-slate-400 font-mono">×{region.multiplier.toFixed(3)}</span>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const [saved, setSaved]           = useState(false);
  const [isAdmin, setIsAdmin]       = useState(false);
  const [settings, setSettings]     = useState({ defaultDiscount: 10, defaultInflation: 5 });
  const [pricingCache, setPricingCache] = useState<PricingCache | null>(null);
  const [refreshing, setRefreshing]     = useState(false);
  const [refreshMsg, setRefreshMsg]     = useState<{ ok: boolean; text: string } | null>(null);
  const [activeCloud, setActiveCloud]   = useState<"aws" | "gcp">("aws");

  // Derived from backend api_status — defaults to true until we hear otherwise
  const awsApiLive = pricingCache?.api_status?.aws?.live_api_configured ?? true;
  const gcpApiLive = pricingCache?.api_status?.gcp?.live_api_configured ?? false;

  useEffect(() => {
    setSettings(getPlatformSettings());
    const stored = localStorage.getItem("businessnext_user");
    if (stored) {
      try { setIsAdmin(JSON.parse(stored)?.role === "admin"); } catch {}
    }
    fetchPricingCache();
  }, []);

  async function fetchPricingCache() {
    try {
      const r = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/pricing/cache`
      );
      if (r.ok) setPricingCache(await r.json());
    } catch {}
  }

  const handleSave = async () => {
    if (!isAdmin) return;
    savePlatformSettings(settings);
    await new Promise((r) => setTimeout(r, 500));
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setRefreshMsg(null);
    try {
      const token = getToken();
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiBase}/api/pricing/refresh`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const body = await res.json();
      if (res.ok) {
        setRefreshMsg({
          ok: true,
          text: `✓ Cache refreshed via ${body.groq_used ? "Groq LLM (LLaMA 3.3 70B)" : "local catalog"} — ${body.aws_saved_count} AWS + ${body.gcp_saved_count} GCP saved regions updated (${new Date(body.refreshed_at).toLocaleTimeString()})`,
        });
        await fetchPricingCache();   // reload displayed data
      } else {
        setRefreshMsg({ ok: false, text: body.detail || "Refresh failed" });
      }
    } catch (e: any) {
      setRefreshMsg({ ok: false, text: e.message || "Network error" });
    } finally {
      setRefreshing(false);
    }
  };

  // Build region lists from cache (fall back to hardcoded if cache not loaded)
  const awsSavedList: RegionEntry[] = Object.entries(
    pricingCache?.aws?.saved_regions ?? {}
  ).map(([id, v]) => ({ id, ...v }));

  const gcpSavedList: RegionEntry[] = Object.entries(
    pricingCache?.gcp?.saved_regions ?? {}
  ).map(([id, v]) => ({ id, ...v }));

  const liveList = activeCloud === "aws" ? ALL_AWS_LIVE : ALL_GCP_LIVE;
  const savedList = activeCloud === "aws" ? awsSavedList : gcpSavedList;

  const lastRefreshed = pricingCache?.meta?.saved_at;

  return (
    <AppShell breadcrumbs={[{ label: "Settings" }]}>
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
          <p className="text-slate-500 text-sm mt-1">Configure platform defaults and pricing parameters</p>
        </motion.div>

        <div className="space-y-5">

          {/* ── Financial Defaults ────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden"
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-blue-600" />
                <h2 className="text-sm font-bold text-slate-900">Financial Defaults</h2>
              </div>
              {!isAdmin && (
                <div className="flex items-center gap-1.5 text-xs text-amber-600 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-full">
                  <Lock className="w-3 h-3" />
                  <span>Admin only — view only</span>
                </div>
              )}
            </div>

            {!isAdmin && (
              <div className="mx-6 mt-4 flex items-start gap-2 text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">
                <ShieldAlert className="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
                <span>These values are set by the platform administrator and applied as defaults during estimation. Contact an admin to change them.</span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-5 px-6 py-5">
              {[
                { key: "defaultDiscount", label: "Default Discount %", hint: "applied to all new estimates" },
                { key: "defaultInflation", label: "Default Inflation %", hint: "applied year-over-year" },
              ].map(({ key, label, hint }) => (
                <div key={key}>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    {label}
                    {isAdmin && <span className="ml-1 text-slate-400 font-normal">({hint})</span>}
                  </label>
                  <input
                    id={`${key}-input`}
                    type="number" min={0} max={100}
                    value={(settings as any)[key]}
                    onChange={(e) =>
                      isAdmin && setSettings((s) => ({ ...s, [key]: parseInt(e.target.value) || 0 }))
                    }
                    readOnly={!isAdmin}
                    className={`w-full px-4 py-3 text-sm border rounded-xl transition-all ${
                      isAdmin
                        ? "border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
                        : "border-slate-200 bg-slate-50 text-slate-500 cursor-not-allowed"
                    }`}
                  />
                </div>
              ))}
            </div>
          </motion.div>

          {/* ── Regions ───────────────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
            className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden"
          >
            <div className="px-6 py-4 border-b border-slate-100">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-violet-600" />
                  <h2 className="text-sm font-bold text-slate-900">Supported Regions</h2>
                </div>
                {/* Cloud toggle */}
                <div className="flex rounded-xl overflow-hidden border border-slate-200 text-xs font-semibold">
                  {(["aws", "gcp"] as const).map((c) => (
                    <button
                      key={c}
                      onClick={() => setActiveCloud(c)}
                      className={`px-4 py-1.5 transition-colors ${
                        activeCloud === c
                          ? "bg-blue-600 text-white"
                          : "bg-white text-slate-500 hover:bg-slate-50"
                      }`}
                    >
                      {c.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> Live regions</span>
                {" "}use real-time pricing APIs.{" "}
                <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400 inline-block" /> Saved regions</span>
                {" "}use cached multiplier-based rates — refresh to update.
              </p>
            </div>

            <div className="px-6 py-5 space-y-5">
              {/* Live */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Wifi className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">Live Pricing</span>
                  <span className="text-xs text-slate-400 ml-1">({liveList.length} regions)</span>
                </div>
              <div className="grid grid-cols-2 gap-2">
                  {liveList.map((r) => (
                    <RegionCard
                      key={r.id}
                      region={{ ...r, multiplier: 1 }}
                      type="live"
                      apiLive={activeCloud === "aws" ? awsApiLive : gcpApiLive}
                    />
                  ))}
                </div>
              </div>

              {/* Saved */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <WifiOff className="w-3.5 h-3.5 text-amber-500" />
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">Saved Catalog</span>
                  <span className="text-xs text-slate-400 ml-1">({savedList.length} regions)</span>
                </div>
                {savedList.length === 0 ? (
                  <p className="text-xs text-slate-400 italic px-2">
                    No saved regions loaded — click Refresh Now to populate from the catalog.
                  </p>
                ) : (
                  <div className="grid grid-cols-2 gap-2">
                    {savedList.map((r) => (
                      <RegionCard
                        key={r.id}
                        region={r}
                        type="saved"
                        apiLive={false}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </motion.div>

          {/* ── Pricing Cache Status ───────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6"
          >
            <div className="flex items-center gap-2 mb-5">
              <Database className="w-4 h-4 text-emerald-600" />
              <h2 className="text-sm font-bold text-slate-900">Pricing Cache Status</h2>
            </div>

            <div className="flex items-center justify-between p-4 bg-emerald-50 rounded-xl border border-emerald-200 mb-4">
              <div className="flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded-full ${refreshing ? "bg-amber-400" : "bg-emerald-500 pulse-dot"}`} />
                <div>
                  <p className="text-sm font-semibold text-emerald-800">
                    {refreshing ? "Refreshing…" : "Cache is Fresh"}
                  </p>
                  <p className="text-xs text-emerald-600">
                    {lastRefreshed
                      ? `Last refreshed: ${formatDate(lastRefreshed)}`
                      : "Refresh to load latest prices"}
                    {pricingCache?.meta?.pricing_date && ` · Prices from: ${pricingCache.meta.pricing_date}`}
                  </p>
                </div>
              </div>
              <button
                id="refresh-pricing-button"
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-emerald-700 bg-emerald-100 rounded-lg hover:bg-emerald-200 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {refreshing
                  ? <><Loader2 className="w-3 h-3 animate-spin" /> Refreshing…</>
                  : <><RefreshCw className="w-3 h-3" /> Refresh Now</>}
              </button>
            </div>

            {refreshMsg && (
              <motion.div
                initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
                className={`flex items-start gap-2 text-xs px-4 py-3 rounded-xl mb-4 border ${
                  refreshMsg.ok
                    ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                    : "text-red-700 bg-red-50 border-red-200"
                }`}
              >
                {refreshMsg.ok
                  ? <CheckCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                  : <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />}
                {refreshMsg.text}
              </motion.div>
            )}

            <div className="grid grid-cols-2 gap-3 text-center">
              {[
                {
                  label: "AWS Pricing API",
                  live: awsApiLive,
                  note: pricingCache?.api_status?.aws?.note ?? "Checking…",
                  source: pricingCache?.api_status?.aws?.source ?? "",
                },
                {
                  label: "GCP Pricing API",
                  live: gcpApiLive,
                  note: pricingCache?.api_status?.gcp?.note ?? "Checking…",
                  source: pricingCache?.api_status?.gcp?.source ?? "",
                },
              ].map((api) => (
                <div key={api.label} className={`p-3 rounded-xl border ${
                  api.live ? "bg-emerald-50 border-emerald-100" : "bg-amber-50 border-amber-100"
                }`}>
                  {api.live
                    ? <CheckCircle className="w-4 h-4 text-emerald-500 mx-auto mb-1" />
                    : <AlertCircle className="w-4 h-4 text-amber-500 mx-auto mb-1" />}
                  <p className="text-xs font-semibold text-slate-700">{api.label}</p>
                  <p className={`text-xs font-semibold mt-0.5 ${
                    api.live ? "text-emerald-600" : "text-amber-600"
                  }`}>
                    {api.live ? "Connected" : "Not Configured"}
                  </p>
                  <p className="text-[10px] text-slate-400 mt-1 leading-tight">{api.note}</p>
                </div>
              ))}
            </div>
          </motion.div>

          {/* ── Save ────────────────────────────────────────────────────────── */}
          <div className="flex justify-end">
            {isAdmin ? (
              <motion.button
                id="save-settings-button"
                onClick={handleSave}
                whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
                className="flex items-center gap-2 px-6 py-3 text-sm font-bold text-white rounded-xl"
                style={{
                  background: saved
                    ? "linear-gradient(135deg, #059669, #047857)"
                    : "linear-gradient(135deg, #2563eb, #1d4ed8)",
                }}
              >
                {saved ? <><CheckCircle className="w-4 h-4" /> Saved!</> : <><Save className="w-4 h-4" /> Save Settings</>}
              </motion.button>
            ) : (
              <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-50 border border-slate-200 px-4 py-3 rounded-xl">
                <Info className="w-3.5 h-3.5" />
                Only admins can save settings changes.
              </div>
            )}
          </div>

        </div>
      </div>
      <AICopilot />
    </AppShell>
  );
}
