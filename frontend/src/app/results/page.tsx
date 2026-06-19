"use client";

import { motion } from "framer-motion";
import { useState, useEffect, Suspense } from "react";
import dynamic from "next/dynamic";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Download, RefreshCw, TrendingUp, TrendingDown,
  DollarSign, Lightbulb, FileSpreadsheet,
  FileText, AlertTriangle, Info, CheckCircle, Loader2,
} from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import AICopilot from "@/components/AICopilot";
import { MOCK_RESULTS } from "@/lib/mock-data";
import { estimatesApi, clientsApi, type EstimateDetail } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

const EChartsReact = dynamic(() => import("echarts-for-react"), { ssr: false });

// All possible tabs — visibility filtered at runtime based on selected environments
const ALL_ENV_TABS = ["Production", "SIT", "UAT", "DR"] as const;
type EnvTab = typeof ALL_ENV_TABS[number];

function ResultsContent() {
  const searchParams = useSearchParams();
  // Accept both "id" (new wizard redirect) and the legacy "estimateId" param
  const estimateId = searchParams.get("id") ?? searchParams.get("estimateId");
  const clientId = searchParams.get("clientId");
  // Quick numbers embedded in the redirect URL by the wizard
  const urlMonthly = parseFloat(searchParams.get("monthly") ?? "0") || 0;
  const urlAnnual  = parseFloat(searchParams.get("annual")  ?? "0") || 0;

  const [estimate, setEstimate] = useState<EstimateDetail | null>(null);
  const [clientName, setClientName] = useState("—");
  const [loading, setLoading] = useState(!!estimateId);
  const [activeEnv, setActiveEnv] = useState<EnvTab>("Production");
  const [activeSection, setActiveSection] = useState("overview");
  const [aiTypeTab, setAiTypeTab] = useState("All");  // AI Services sub-tab filter
  const router = useRouter();

  // Fallback to mock data when no estimateId is in the URL (e.g. navigated directly)
  const r = MOCK_RESULTS;

  useEffect(() => {
    if (!estimateId) {
      setLoading(false);
      return;
    }
    const load = async () => {
      setLoading(true);
      try {
        const [estData] = await Promise.all([
          estimatesApi.get(estimateId),
        ]);
        setEstimate(estData);
        setClientName(estData.customerName);

        // Also try to get the client name from the client ID
        if (estData.clientId) {
          try {
            const c = await clientsApi.get(estData.clientId);
            setClientName(c.name);
          } catch {/* use customerName as fallback */}
        }
      } catch (err) {
        // On failure, fall back to mock data gracefully
        setEstimate(null);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [estimateId]);

  // Use real data when available; fall back first to URL params, then mock
  const awsMonthlyCost = estimate?.awsMonthlyCost ?? (urlMonthly || r.awsMonthlyCost);
  const awsAnnualCost  = estimate?.awsAnnualCost  ?? (urlAnnual  || r.awsAnnualCost);
  const aws5YearTCO    = estimate?.aws5YearTCO    ?? r.aws5YearTCO;
  const gcpMonthlyCost = estimate?.gcpMonthlyCost ?? r.gcpMonthlyCost;
  const awsSavingsVsGcp = estimate?.awsSavingsVsGcp ?? r.awsSavingsVsGcp;
  const savingsPercent = estimate?.savingsPercent ?? r.savingsPercent;
  const version = estimate?.version ?? r.version;
  const generatedAt = estimate?.generatedAt ?? r.generatedAt;
  const gcp5YearTCO = gcpMonthlyCost * 12 * 5;

  // ── Cloud provider flags — drives conditional GCP UI visibility ────────
  const _providers = estimate?.cloudProviders ?? ["AWS"];
  const hasAws = _providers.includes("AWS") || _providers.length === 0;
  const hasGcp = _providers.includes("GCP");

  // ── Grand totals across ALL environments ──────────────────────────────
  // estimate.environments is the env_pricing dict from env_pricer.py
  type PricedRole = {
    label: string; category?: string;
    nodes: number; vcpu_per_node?: number | string; ram_per_node?: number | string;
    storage_per_node_gb?: number; instance_type?: string; monthly_usd: number;
  };
  const envData = estimate?.environments as {
    preprod_sit_uat?: {
      monthly_usd?: number; annual_usd?: number; per_env_monthly?: number;
      priced_roles?: PricedRole[];
    };
    dr?: {
      monthly_usd?: number; annual_usd?: number;
      five_year_forecast?: { five_year_total?: number };
      priced_roles?: PricedRole[];
    };
    combined_monthly?: number;
  } | null;

  const ppMonthly = envData?.preprod_sit_uat?.monthly_usd ?? 0;   // SIT+UAT combined (2×)
  const drMonthly = envData?.dr?.monthly_usd ?? 0;                 // DR monthly

  // ── Split pricedRoles into AI services vs core infrastructure ──────────────
  type AugRole = { label: string; instance_type?: string; vcpu_per_node?: number|string; ram_per_node?: number|string;
    storage_per_node_gb?: number; nodes: number; monthly_usd: number; category?: string; role_key?: string; [k:string]: unknown };
  const _allRoles = (estimate?.pricedRoles ?? []) as AugRole[];
  const _isAiRole = (r: AugRole) =>
    r.category === "AI Services" ||
    ["p3.","p4.","p5.","g4.","g5."].some(p => (r.instance_type ?? "").startsWith(p)) ||
    (r.role_key ?? "").startsWith("ai_");
  const _aiRoles   = _allRoles.filter(_isAiRole);
  const _coreRoles = _allRoles.filter(r => !_isAiRole(r));
  const hasAi = _aiRoles.length > 0 || !!(estimate?.metrics as Record<string,unknown>)?.ai_services;

  // Real production cost from actual priced roles (ALL roles — for financial accuracy)
  const realProdRows = _coreRoles
    .filter(role => role.nodes > 0)
    .map(role => ({
      role:     role.label,
      instance: role.instance_type ?? "\u2014",
      vcpu:     role.vcpu_per_node ?? "\u2014",
      ram:      role.ram_per_node ?? "\u2014",
      storage:  role.storage_per_node_gb ? `${role.storage_per_node_gb} GB` : "\u2014",
      quantity: role.nodes,
      cost:     role.monthly_usd,
    }));

  const aiDisplayRows = _aiRoles
    .filter(role => role.nodes > 0 || (role.monthly_usd ?? 0) > 0)
    .map(role => ({
      role:       role.label,
      type:       (role.role_key ?? "").includes("predictive") ? "Predictive AI" :
                  (role.role_key ?? "").includes("genai") ? "Generative AI" :
                  (role.role_key ?? "").includes("agentic") ? "Agentic AI" :
                  (role.role_key ?? "").includes("bedrock") ? "Managed API" : "AI Service",
      instance:   role.instance_type ?? "\u2014",
      vcpu:       role.vcpu_per_node ?? "\u2014",
      ram:        role.ram_per_node ?? "\u2014",
      nodes:      role.nodes,
      monthly:    role.monthly_usd,
      note:       (role as any).note ?? "",
    }));

  const aiMonthly = _aiRoles.reduce((s, r) => s + (r.monthly_usd ?? 0), 0);
  const aiAnnual  = aiMonthly * 12;

  // realProdMonthly = ALL production roles (core + AI) — used in grand totals
  const realProdMonthly = _allRoles.filter(r => r.nodes > 0 || (r.monthly_usd ?? 0) > 0)
    .reduce((s, r) => s + (r.monthly_usd ?? 0), 0) || awsMonthlyCost;

  const grandMonthly  = realProdMonthly + ppMonthly + drMonthly;
  const grandAnnual   = grandMonthly * 12;

  // 5-year with 4% annual inflation: sum(monthly×12×(1.04^y) for y=1..5) ≈ factor 5.633
  const INFLATION_FACTOR_5Y = [1, 2, 3, 4, 5].reduce((s, y) => s + Math.pow(1.04, y), 0);
  const prod5Y   = aws5YearTCO;   // already inflation-adjusted by backend
  const pp5Y     = ppMonthly * 12 * INFLATION_FACTOR_5Y;
  const dr5Y     = envData?.dr?.five_year_forecast?.five_year_total ?? (drMonthly * 12 * INFLATION_FACTOR_5Y);
  const grand5YearTCO = prod5Y + pp5Y + dr5Y;



  const comparisonOption = {
    tooltip: { trigger: "axis", backgroundColor: "#1e293b", borderColor: "#334155", textStyle: { color: "#f8fafc" }, formatter: (p: { name: string; data: number }[]) => `${p[0].name}<br/>$${p[0].data.toLocaleString()}` },
    grid: { left: "5%", right: "5%", bottom: "3%", top: "10px", containLabel: true },
    xAxis: { type: "value", axisLabel: { color: "#94a3b8", fontSize: 11, formatter: (v: number) => `$${(v / 1000).toFixed(0)}k` }, splitLine: { lineStyle: { color: "#f1f5f9", type: "dashed" } } },
    yAxis: { type: "category", data: ["GCP (5Y)", "AWS (5Y)"], axisLabel: { color: "#64748b", fontSize: 12 }, axisLine: { show: false }, axisTick: { show: false } },
    series: [{ type: "bar", barWidth: 28, borderRadius: [0, 8, 8, 0],
      data: [
        { value: gcp5YearTCO, itemStyle: { color: { type: "linear", x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: "#7c3aed" }, { offset: 1, color: "#a78bfa" }] } } },
        { value: aws5YearTCO, itemStyle: { color: { type: "linear", x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: "#2563eb" }, { offset: 1, color: "#60a5fa" }] } } },
      ],
      label: { show: true, position: "right", color: "#64748b", fontSize: 12, formatter: (p: { value: number }) => `$${(p.value / 1000).toFixed(0)}k` },
    }],
  };

  const mockInfra = (r.infrastructure as Record<string, typeof r.infrastructure.production>)[activeEnv.toLowerCase() as keyof typeof r.infrastructure];

  // Helper: extract storage GB from legacy note strings
  // Handles "× 500GB gp3 SAN", "+ 256GB EBS", "1TiB" etc.
  const _storFromNote = (note?: string): number | null => {
    if (!note) return null;
    const matches = [...note.matchAll(/(\d+(?:\.\d+)?)\s*(TB|TiB|GB|GiB)\b/gi)];
    if (!matches.length) return null;
    // Take the largest value (storage is always the biggest number in env_pricer notes)
    let maxGb = 0;
    for (const m of matches) {
      const val = parseFloat(m[1]);
      const unit = m[2].toUpperCase();
      const gb = unit.startsWith("T") ? Math.round(val * 1024) : Math.round(val);
      if (gb > maxGb) maxGb = gb;
    }
    return maxGb > 0 ? maxGb : null;
  };

  // Helper: convert env priced_roles to infra table row shape
  // env_pricer uses "vcpu"/"ram"; aws_pricer uses "vcpu_per_node"/"ram_per_node" — handle both
  // For old estimates without storage_per_node_gb, fall back to parsing the note field
  const mapEnvRoles = (roles: PricedRole[] | undefined) =>
    (roles ?? []).filter(role => role.nodes > 0).map(role => {
      const r = role as PricedRole & { vcpu?: number; ram?: number; storage?: number; note?: string };
      const vcpuVal = r.vcpu_per_node ?? r.vcpu;
      const ramVal  = r.ram_per_node  ?? r.ram;
      const storVal = r.storage_per_node_gb ?? r.storage ?? _storFromNote(r.note) ?? null;
      return {
        role:     r.label,
        instance: r.instance_type ?? "—",
        vcpu:     vcpuVal != null && Number(vcpuVal) > 0 ? vcpuVal : "—",
        ram:      ramVal  != null && Number(ramVal)  > 0 ? `${ramVal} GB` : "—",
        storage:  storVal != null && Number(storVal) > 0 ? `${storVal} GB` : "—",
        quantity: r.nodes,
        cost:     r.monthly_usd,
      };
    });


  const realSitUatRows = mapEnvRoles(envData?.preprod_sit_uat?.priced_roles);
  const realDrRows     = mapEnvRoles(envData?.dr?.priced_roles);

  // Select real rows per tab; fall back to mock when not available
  const currentInfra =
    activeEnv === "Production" && realProdRows.length > 0  ? realProdRows :
    activeEnv === "SIT"        && realSitUatRows.length > 0 ? realSitUatRows :
    activeEnv === "UAT"        && realSitUatRows.length > 0 ? realSitUatRows :
    activeEnv === "DR"         && realDrRows.length > 0     ? realDrRows :
    (mockInfra ?? []);

  // ── Dynamic env tabs — only show environments that have real data ────────
  const hasSitUat = (envData?.preprod_sit_uat?.monthly_usd ?? 0) > 0;
  const hasDr     = (envData?.dr?.monthly_usd ?? 0) > 0;
  const visibleTabs: EnvTab[] = [
    "Production",
    ...(hasSitUat ? (["SIT", "UAT"] as EnvTab[]) : []),
    ...(hasDr     ? (["DR"]          as EnvTab[]) : []),
  ];

  // ── Real environment breakdown data for chart + legend ───────────────────
  // per_env_monthly = single SIT or UAT cost; fallback to half of combined when not stored
  const perSitMonthly = envData?.preprod_sit_uat?.per_env_monthly
    ?? (ppMonthly > 0 ? ppMonthly / 2 : 0);
  const realEnvBreakdown: { name: string; value: number }[] = [
    { name: "Production", value: realProdMonthly },
    ...(hasSitUat ? [{ name: "SIT", value: perSitMonthly }, { name: "UAT", value: perSitMonthly }] : []),
    ...(hasDr     ? [{ name: "DR",  value: drMonthly }] : []),
  ].filter(e => e.value > 0);

  const envBreakdownOption = {
    tooltip: { trigger: "item", formatter: (p: { name: string; value: number }) => `${p.name}: $${p.value.toLocaleString()}/mo` },
    legend: { bottom: 0, textStyle: { color: "#64748b", fontSize: 11 } },
    series: [{ type: "pie", radius: ["50%", "75%"], center: ["50%", "45%"],
      data: realEnvBreakdown,
      itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 }, label: { show: false },
      color: ["#2563eb", "#7c3aed", "#059669", "#f59e0b"],
    }],
  };

  // Production cost grouped by category (for overview chart)
  const prodCostByCategory = realProdRows.reduce<Record<string, number>>((acc, row) => {
    // Determine category from the role label heuristic
    const lbl = row.role.toLowerCase();
    const cat =
      lbl.includes("k8s") || lbl.includes("eks") || lbl.includes("worker") || lbl.includes("kubernetes") ? "Kubernetes" :
      lbl.includes("db") || lbl.includes("postgres") || lbl.includes("sql") || lbl.includes("oracle") || lbl.includes("redis") || lbl.includes("cache") ? "Database & Cache" :
      lbl.includes("s3") || lbl.includes("backup") ? "Storage" :
      lbl.includes("nat") || lbl.includes("alb") || lbl.includes("load") || lbl.includes("bastion") || lbl.includes("ecr") ? "Infrastructure" :
      lbl.includes("cloudwatch") || lbl.includes("monitor") ? "Monitoring" :
      lbl.includes("ai") || lbl.includes("bedrock") ? "AI Services" :
      "Other";
    acc[cat] = (acc[cat] ?? 0) + row.cost;
    return acc;
  }, {});

  // Filter out zero-value categories so bar chart is clean
  const categoryChartData = Object.entries(prodCostByCategory)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1]);

  // Premium horizontal bar with real values, percentage, and gradients
  const CATEGORY_COLORS_START = ["#2563eb","#7c3aed","#059669","#f59e0b","#ef4444","#0891b2","#64748b"];
  const CATEGORY_COLORS_END   = ["#60a5fa","#a78bfa","#34d399","#fcd34d","#f87171","#38bdf8","#94a3b8"];
  const prodCategoryOption = {
    tooltip: {
      trigger: "axis", axisPointer: { type: "none" },
      backgroundColor: "#1e293b", borderColor: "#334155",
      textStyle: { color: "#f8fafc", fontSize: 12 },
      formatter: (p: { name: string; value: number }[]) =>
        `<b>${p[0].name}</b><br/>$${p[0].value.toLocaleString()}/mo<br/>${realProdMonthly > 0 ? (p[0].value / realProdMonthly * 100).toFixed(1) : 0}% of prod`,
    },
    grid: { left: "2%", right: "2%", bottom: "4%", top: "4%", containLabel: true },
    xAxis: { show: false, type: "value" },
    yAxis: {
      type: "category",
      data: categoryChartData.map(([k]) => k),
      axisLabel: { color: "#475569", fontSize: 12, fontWeight: "600" },
      axisLine: { show: false }, axisTick: { show: false },
    },
    series: [{
      type: "bar",
      barWidth: 26,
      barCategoryGap: "32%",
      borderRadius: [0, 10, 10, 0],
      data: categoryChartData.map(([, v], i) => ({
        value: Math.round(v),
        itemStyle: { color: {
          type: "linear", x: 0, y: 0, x2: 1, y2: 0,
          colorStops: [
            { offset: 0, color: CATEGORY_COLORS_START[i % CATEGORY_COLORS_START.length] },
            { offset: 1, color: CATEGORY_COLORS_END[i % CATEGORY_COLORS_END.length] },
          ],
        }},
      })),
      label: {
        show: true, position: "right", distance: 8,
        fontSize: 12, fontWeight: "bold", color: "#1e293b",
        formatter: (p: { value: number }) => {
          const pct = realProdMonthly > 0 ? (p.value / realProdMonthly * 100).toFixed(0) : 0;
          return `$${p.value.toLocaleString()}  ${pct}%`;
        },
      },
      emphasis: { itemStyle: { opacity: 0.85 } },
    }],
  };

  const envTotalMonthly = realEnvBreakdown.reduce((s, e) => s + e.value, 0);
  const ENV_COLORS = ["#2563eb", "#7c3aed", "#059669", "#f59e0b", "#ef4444", "#0891b2"];

  // CRM-module env breakdown — excludes AI costs from production so the env chart
  // reflects only CRM infrastructure spend (AI has its own tab)
  const crmProdMonthly = Math.max(0, realProdMonthly - aiMonthly);
  const crmEnvBreakdown: { name: string; value: number }[] = [
    { name: "Production", value: crmProdMonthly },
    ...(hasSitUat ? [{ name: "SIT", value: perSitMonthly }, { name: "UAT", value: perSitMonthly }] : []),
    ...(hasDr     ? [{ name: "DR",  value: drMonthly }] : []),
  ].filter(e => e.value > 0);
  const crmTotalMonthly = crmEnvBreakdown.reduce((s, e) => s + e.value, 0);

  // Horizontal bar chart for the CRM env panel — clearly legible even when prod dominates
  const envCompareOption = {
    tooltip: {
      trigger: "axis", axisPointer: { type: "shadow" },
      backgroundColor: "#1e293b", borderColor: "#334155",
      textStyle: { color: "#f8fafc", fontSize: 12 },
      formatter: (params: { name: string; value: number }[]) => {
        const p = params[0];
        const pct = crmTotalMonthly > 0 ? (p.value / crmTotalMonthly * 100).toFixed(1) : 0;
        return `<b>${p.name}</b><br/>Monthly: $${p.value.toLocaleString()}<br/>Annual: $${(p.value * 12).toLocaleString()}<br/>${pct}% of CRM total`;
      },
    },
    grid: { left: 80, right: 90, top: 8, bottom: 8, containLabel: false },
    xAxis: { type: "value", show: false },
    yAxis: {
      type: "category",
      data: crmEnvBreakdown.map(e => e.name),
      axisLabel: { color: "#475569", fontSize: 12, fontWeight: "600" },
      axisLine: { show: false }, axisTick: { show: false },
    },
    series: [{
      type: "bar", barWidth: 22, borderRadius: [0, 8, 8, 0],
      data: crmEnvBreakdown.map((e, i) => ({
        value: Math.round(e.value),
        itemStyle: { color: { type: "linear", x:0,y:0,x2:1,y2:0,
          colorStops: [{ offset:0, color: ENV_COLORS[i % ENV_COLORS.length] }, { offset:1, color: ENV_COLORS[i % ENV_COLORS.length] + "cc" }] } },
      })),
      label: {
        show: true, position: "right", distance: 6,
        fontSize: 11, fontWeight: "bold", color: "#1e293b",
        formatter: (p: { value: number }) => `$${p.value.toLocaleString()}/mo`,
      },
    }],
  };


  if (loading) {
    return (
      <AppShell breadcrumbs={[{ label: "Clients", href: "/clients" }, { label: "Loading..." }]}>
        <div className="flex items-center justify-center py-32 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mr-3" />
          <span className="text-sm">Loading estimate results...</span>
        </div>
      </AppShell>
    );
  }

  // ── Dynamic AI recommendations from real estimate data ──────────────────
  const dynamicRecs: { type: "warning" | "tip" | "info"; title: string; desc: string }[] = [];
  const firstProd = (estimate?.pricedRoles ?? [])[0];
  const itype = firstProd?.instance_type ?? "";
  if (itype.includes("r6a") || itype.includes("c6a"))
    dynamicRecs.push({ type: "warning", title: "Memory-Optimized Instances (r6a)",
      desc: "Selected r6a AMD instances save cost by ~18% vs m6i for your memory-heavy workload." });
  else if (itype.includes("m6i") || itype.includes("m5"))
    dynamicRecs.push({ type: "tip", title: "Consider AMD Instances (r6a/c6a)",
      desc: `Switching from ${itype.split(".")[0]} to AMD r6a family could save ~18% on compute costs.` });
  const annualRI = Math.round(realProdMonthly * 12 * 0.38);
  if (annualRI > 0)
    dynamicRecs.push({ type: "tip", title: "Reserved Instance (3 Year)",
      desc: `Switching to 3-Year Reserved would reduce cost by ~${formatCurrency(Math.round(realProdMonthly * 0.38))}/month (~38% savings).` });
  if (awsSavingsVsGcp > 5000)
    dynamicRecs.push({ type: "info", title: `AWS Saves ${formatCurrency(awsSavingsVsGcp)}/yr vs GCP`,
      desc: `For equivalent services in ${estimate?.gcpRegion ?? "GCP"}, AWS is significantly cheaper on r6a AMD instances.` });
  else if (awsSavingsVsGcp < -1000)
    dynamicRecs.push({ type: "info", title: `GCP Saves ${formatCurrency(Math.abs(awsSavingsVsGcp))}/yr`,
      desc: `GCP ${estimate?.gcpRegion ?? ""} is cheaper for this workload. Evaluate if cloud flexibility is acceptable.` });
  if (hasDr && drMonthly > 0)
    dynamicRecs.push({ type: "info", title: "Consider Active-Active vs DR",
      desc: `DR environment contributes ${formatCurrency(drMonthly)}/month. Evaluate if active-active architecture could consolidate this cost.` });
  const envCount = visibleTabs.length;
  if (envCount >= 3)
    dynamicRecs.push({ type: "tip", title: "Multi-Environment Cost Optimization",
      desc: `You have ${envCount} environments. Consider shared lower-env clusters (SIT+UAT) to reduce non-production spend.` });
  const aiRecs = dynamicRecs.length > 0 ? dynamicRecs : r.aiRecommendations;


  return (
    <AppShell breadcrumbs={[
      { label: "Clients", href: "/clients" },
      {
        label: clientName,
        ...((clientId || estimate?.clientId)
          ? { href: `/clients/${clientId || estimate?.clientId}/estimates` }
          : {}),
      },
      { label: "Results" }
    ]}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-slate-900">Estimate Results</h1>
              <span className="px-3 py-1 bg-emerald-100 text-emerald-700 text-xs font-bold rounded-full flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> Completed
              </span>
              {estimate && <span className="px-2 py-0.5 bg-blue-50 text-blue-600 text-xs font-semibold rounded-lg border border-blue-100">Live Data</span>}
            </div>
            <p className="text-slate-500 text-sm">{clientName} · {version} · Generated {generatedAt}</p>
          </div>
          <div className="flex gap-2">
            <button 
              onClick={() => {
                const targetClientId = clientId || estimate?.clientId;
                const targetEstimateId = estimateId || estimate?.id;
                if (targetEstimateId) {
                  router.push(`/estimate/new?recalculate=${targetEstimateId}&clientId=${targetClientId ?? ""}`);
                } else {
                  router.push(`/estimate/new?clientId=${targetClientId ?? ""}`);
                }
              }}
              className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors">
              <RefreshCw className="w-4 h-4" /> Recalculate
            </button>
            {estimateId && (
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                onClick={() => {
                  const token = localStorage.getItem("businessnext_token");
                  window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/estimates/${estimateId}/download-all?token=${token}`, "_blank");
                }}
                className="flex items-center gap-2 px-5 py-2 text-sm font-bold text-white rounded-xl btn-shine"
                style={{ background: "linear-gradient(135deg, #2563eb, #1d4ed8)" }}>
                <Download className="w-4 h-4" /> Download All (.zip)
              </motion.button>
            )}
          </div>
        </motion.div>

        {/* Tab nav — dynamic based on modules/providers */}
        <div className="flex gap-1 bg-white border border-slate-200 rounded-2xl p-1.5 mb-6 w-fit shadow-sm">
          {([
            { id: "overview",                  label: "Overview" },
            { id: "Infrastructure Sizing",     label: "Infrastructure Sizing" },
            ...(hasAi ? [{ id: "AI Services", label: "🤖 AI Services" }] : []),
            { id: "Cloud Services Breakdown",  label: "Cloud Services Breakdown" },
            { id: "AI Insights",               label: "AI Insights" },
          ] as { id: string; label: string }[]).map((tab) => (
            <button key={tab.id} onClick={() => setActiveSection(tab.id)}
              className={`px-4 py-2 text-xs font-semibold rounded-xl transition-all ${
                activeSection === tab.id ? "text-white shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
              style={activeSection === tab.id ? { background: "linear-gradient(135deg, #2563eb, #1d4ed8)" } : {}}>
              {tab.label}
            </button>
          ))}
        </div>

        {/* KPI Cards — always visible */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            {
              label: "Total Monthly (All Envs)",
              value: grandMonthly,
              sub: `Prod ${formatCurrency(awsMonthlyCost)} · SIT+UAT ${formatCurrency(ppMonthly)} · DR ${formatCurrency(drMonthly)}`,
              up: true,
            },
            {
              label: "Total Annual (All Envs)",
              value: grandAnnual,
              sub: `Prod ${formatCurrency(awsAnnualCost)} / year`,
              up: true,
            },
            {
              label: "5 Year TCO (All Envs)",
              value: grand5YearTCO,
              sub: `Prod ${formatCurrency(prod5Y)} · Envs ${formatCurrency(pp5Y + dr5Y)}`,
              up: true,
            },
            ...(hasGcp ? [{
              label: "AWS Savings vs GCP",
              value: awsSavingsVsGcp,
              sub: `${savingsPercent}% savings on production`,
              up: false,
            }] : []),
          ].map((kpi, i) => (
            <motion.div key={kpi.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
              className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 hover:shadow-md transition-shadow">
              <p className="text-xs text-slate-500 mb-2 font-medium">{kpi.label}</p>
              <p className="text-2xl font-bold text-slate-900 mb-1">{formatCurrency(kpi.value)}</p>
              <p className="text-[10px] text-slate-400 leading-tight">{kpi.sub}</p>
            </motion.div>
          ))}
        </div>

        {/* AWS vs GCP 5 Year TCO chart — only when GCP was selected */}
        {hasGcp && (activeSection === "overview" || activeSection === "Cost Projections") && (
        <div className="grid grid-cols-1 mb-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-sm font-bold text-slate-900 mb-1">AWS vs GCP — 5 Year TCO (Production Only)</h3>
            <div className="flex items-center gap-2 mb-4">
              {awsSavingsVsGcp >= 0
                ? <span className="px-2.5 py-1 bg-emerald-100 text-emerald-700 text-xs font-bold rounded-full">AWS cheaper by {formatCurrency(awsSavingsVsGcp)}/yr</span>
                : <span className="px-2.5 py-1 bg-violet-100 text-violet-700 text-xs font-bold rounded-full">GCP cheaper by {formatCurrency(Math.abs(awsSavingsVsGcp))}/yr</span>
              }
              {estimate?.gcpRegion && (
                <span className="text-[10px] text-slate-400">{estimate.gcpRegion} vs {estimate.metrics?.aws_region as string ?? ""}</span>
              )}
            </div>
            <EChartsReact option={comparisonOption} style={{ height: 180 }} />
          </div>
        </div>
        )}

        {/* AWS vs GCP Production Comparison — Cost Projections tab, only when GCP selected */}
        {hasGcp && activeSection === "Cost Projections" && (() => {
          const gcpAnnual = gcpMonthlyCost * 12;
          const compRows = [
            { label: "Monthly",    aws: awsMonthlyCost, gcp: gcpMonthlyCost },
            { label: "Annual",     aws: awsAnnualCost,  gcp: gcpAnnual },
            { label: "5 Year TCO", aws: aws5YearTCO,    gcp: gcp5YearTCO },
          ];
          const groupedBarOption = {
            tooltip: { trigger: "axis", backgroundColor: "#1e293b", borderColor: "#334155", textStyle: { color: "#f8fafc" } },
            legend: { data: ["AWS", "GCP"], textStyle: { color: "#64748b", fontSize: 12 }, top: 0 },
            grid: { left: "3%", right: "4%", bottom: "3%", top: "45px", containLabel: true },
            xAxis: { type: "category", data: ["Monthly", "Annual", "5 Year TCO"], axisLine: { lineStyle: { color: "#e2e8f0" } }, axisTick: { show: false }, axisLabel: { color: "#94a3b8", fontSize: 12 } },
            yAxis: { type: "value", axisLabel: { color: "#94a3b8", fontSize: 11, formatter: (v: number) => `$${(v/1000).toFixed(0)}k` }, splitLine: { lineStyle: { color: "#f1f5f9", type: "dashed" } }, axisLine: { show: false }, axisTick: { show: false } },
            series: [
              { name: "AWS", type: "bar", barWidth: 28, borderRadius: [6,6,0,0],
                itemStyle: { color: { type: "linear", x:0,y:0,x2:0,y2:1, colorStops:[{offset:0,color:"#2563eb"},{offset:1,color:"#60a5fa"}] } },
                data: compRows.map(r => r.aws),
                label: { show: true, position: "top", fontSize: 10, color: "#2563eb", formatter: (p: {value:number}) => `$${(p.value/1000).toFixed(1)}k` } },
              { name: "GCP", type: "bar", barWidth: 28, borderRadius: [6,6,0,0],
                itemStyle: { color: { type: "linear", x:0,y:0,x2:0,y2:1, colorStops:[{offset:0,color:"#7c3aed"},{offset:1,color:"#a78bfa"}] } },
                data: compRows.map(r => r.gcp),
                label: { show: true, position: "top", fontSize: 10, color: "#7c3aed", formatter: (p: {value:number}) => `$${(p.value/1000).toFixed(1)}k` } },
            ],
          };
          return (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mb-6">
              <div className="flex items-center gap-3 mb-4">
                <h3 className="text-base font-bold text-slate-900">Production — AWS vs GCP Comparison</h3>
                <span className={`px-3 py-1 text-xs font-bold rounded-full ${awsSavingsVsGcp >= 0 ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>
                  {awsSavingsVsGcp >= 0 ? `AWS saves ${formatCurrency(awsSavingsVsGcp)}/yr` : `GCP saves ${formatCurrency(Math.abs(awsSavingsVsGcp))}/yr`}
                </span>
              </div>
              <div className="grid grid-cols-5 gap-5">
                {/* Grouped Bar Chart */}
                <div className="col-span-3 bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                  <p className="text-xs text-slate-500 font-medium mb-3">Cost Comparison by Period (Production)</p>
                  <EChartsReact option={groupedBarOption} style={{ height: 260 }} />
                </div>
                {/* Table */}
                <div className="col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                  <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50">
                    <p className="text-xs font-bold text-slate-700 uppercase tracking-wide">Detailed Breakdown — Production</p>
                  </div>
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-100">
                        <th className="text-left px-5 py-2.5 text-xs font-semibold text-slate-500">Period</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-blue-600">AWS</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-violet-600">GCP</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500">Diff</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500">Winner</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {compRows.map((row) => {
                        const diff = row.aws - row.gcp;
                        const pct = row.gcp > 0 ? Math.abs(diff / row.gcp * 100).toFixed(1) : "0";
                        const awsWins = diff <= 0;
                        return (
                          <tr key={row.label} className="hover:bg-slate-50 transition-colors">
                            <td className="px-5 py-3 text-sm font-medium text-slate-700">{row.label}</td>
                            <td className="px-4 py-3 text-right text-sm font-bold text-blue-600">{formatCurrency(row.aws)}</td>
                            <td className="px-4 py-3 text-right text-sm font-bold text-violet-600">{formatCurrency(row.gcp)}</td>
                            <td className={`px-4 py-3 text-right text-xs font-semibold ${awsWins ? "text-emerald-600" : "text-red-500"}`}>
                              {awsWins ? "−" : "+"}{pct}%
                            </td>
                            <td className="px-4 py-3 text-right">
                              <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${awsWins ? "bg-blue-100 text-blue-700" : "bg-violet-100 text-violet-700"}`}>
                                {awsWins ? "AWS" : "GCP"}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot>
                      <tr className="border-t border-slate-200 bg-slate-50">
                        <td colSpan={3} className="px-5 py-3 text-xs font-semibold text-slate-600">
                          {awsSavingsVsGcp >= 0 ? "AWS Annual Savings" : "GCP Annual Savings"}
                        </td>
                        <td colSpan={2} className="px-4 py-3 text-right text-sm font-bold text-emerald-600">
                          {formatCurrency(Math.abs(awsSavingsVsGcp))} · {Math.abs(savingsPercent)}%
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              {/* Per-category AWS vs GCP breakdown */}
              {(estimate?.gcpComparison?.category_comparison ?? []).length > 0 && (
              <div className="mt-5 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
                  <p className="text-xs font-bold text-slate-700 uppercase tracking-wide">AWS vs GCP — Cost by Service Category</p>
                  <span className="text-[10px] text-slate-400">
                    AWS ({estimate?.metrics?.aws_region as string}) vs GCP ({estimate?.gcpRegion})
                  </span>
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-100">
                      {["Category", "AWS/mo", "GCP/mo", "Diff", "Cheaper"].map(h => (
                        <th key={h} className="text-left px-5 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {(estimate?.gcpComparison?.category_comparison ?? []).map((cat) => (
                      <tr key={cat.category} className="hover:bg-slate-50 transition-colors">
                        <td className="px-5 py-2.5 text-sm font-medium text-slate-700">{cat.category}</td>
                        <td className="px-5 py-2.5 text-sm font-bold text-blue-600">{formatCurrency(cat.aws_monthly)}</td>
                        <td className="px-5 py-2.5 text-sm font-bold text-violet-600">{formatCurrency(cat.gcp_monthly)}</td>
                        <td className={`px-5 py-2.5 text-xs font-semibold ${
                          cat.cheaper === "AWS" ? "text-emerald-600" : "text-red-500"}`}>
                          {cat.cheaper === "AWS" ? "−" : "+"}{Math.abs(cat.pct_diff).toFixed(1)}%
                        </td>
                        <td className="px-5 py-2.5">
                          <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                            cat.cheaper === "AWS" ? "bg-blue-100 text-blue-700" : "bg-violet-100 text-violet-700"}`}>
                            {cat.cheaper}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              )}
            </motion.div>
          );
        })()}

        {/* Per-role AWS vs GCP machine table — Cost Projections tab, only when GCP selected */}
        {hasGcp && activeSection === "Cost Projections" && (estimate?.gcpPricedRoles ?? []).length > 0 && (() => {
          // Parse GCP vCPU/RAM from instance type name (e.g. n2-highmem-16 → 16 vCPU, 128 GB)
          const parseGcpSpec = (itype?: string) => {
            if (!itype) return { vcpu: null as number | null, ram: null as number | null };
            const m = itype.match(/n\d[a-z]*-(highmem|standard|highcpu|ultramem)-(\d+)/i);
            if (!m) return { vcpu: null as number | null, ram: null as number | null };
            const v = parseInt(m[2]);
            const fam = m[1].toLowerCase();
            const ram = fam === "highmem" ? v * 8 : fam === "standard" ? v * 4 : fam === "highcpu" ? Math.round(v * 0.9) : null;
            return { vcpu: v, ram };
          };

          const gcpMap = new Map((estimate?.gcpPricedRoles ?? []).map(r => [r.role_key, r]));
          const awsRoles = estimate?.pricedRoles ?? [];
          const rows = awsRoles.map(a => {
            const g = gcpMap.get(a.role_key);
            const awsMo  = a.monthly_usd ?? 0;
            const gcpMo  = g?.monthly_usd ?? 0;
            const diff   = awsMo > 0 && gcpMo > 0 ? ((awsMo - gcpMo) / gcpMo * 100) : null;
            return { ...a, gcpRole: g, awsMo, gcpMo, diff };
          }).filter(r => r.awsMo > 0 || r.gcpMo > 0);

          return (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="mt-5 mb-6">
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
                  <p className="text-xs font-bold text-slate-700 uppercase tracking-wide">
                    Per-Role Machine Config — AWS vs GCP
                  </p>
                  <span className="text-[10px] text-slate-400">
                    {estimate?.metrics?.aws_region as string} vs {estimate?.gcpRegion}
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-slate-100 bg-slate-50/50">
                        <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase tracking-wide w-48">Role</th>
                        {/* AWS columns */}
                        <th className="text-left px-3 py-2.5 font-semibold text-blue-500 uppercase tracking-wide">AWS Instance</th>
                        <th className="text-right px-3 py-2.5 font-semibold text-blue-500 uppercase tracking-wide">vCPU</th>
                        <th className="text-right px-3 py-2.5 font-semibold text-blue-500 uppercase tracking-wide">RAM</th>
                        <th className="text-right px-3 py-2.5 font-semibold text-blue-600 uppercase tracking-wide">AWS/mo</th>
                        {/* GCP columns */}
                        <th className="text-left px-3 py-2.5 font-semibold text-violet-500 uppercase tracking-wide border-l border-slate-100">GCP Instance</th>
                        <th className="text-right px-3 py-2.5 font-semibold text-violet-500 uppercase tracking-wide">vCPU</th>
                        <th className="text-right px-3 py-2.5 font-semibold text-violet-500 uppercase tracking-wide">RAM</th>
                        <th className="text-right px-3 py-2.5 font-semibold text-violet-600 uppercase tracking-wide">GCP/mo</th>
                        <th className="text-right px-3 py-2.5 font-semibold text-slate-500 uppercase tracking-wide">Winner</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {rows.map((row) => {
                        const awsWins = row.awsMo <= row.gcpMo && row.awsMo > 0;
                        const diffStr = row.diff !== null ? `${row.diff > 0 ? "+" : ""}${row.diff.toFixed(0)}%` : "—";
                        return (
                          <tr key={row.role_key} className="hover:bg-slate-50 transition-colors">
                            <td className="px-4 py-2.5">
                              <p className="font-medium text-slate-700 leading-tight truncate max-w-[180px]" title={row.label}>{row.label}</p>
                              <p className="text-[10px] text-slate-400 mt-0.5">{row.category}</p>
                            </td>
                            {/* AWS side */}
                            <td className="px-3 py-2.5">
                              <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded font-mono font-semibold">{row.instance_type ?? "—"}</span>
                            </td>
                            <td className="px-3 py-2.5 text-right text-slate-600">{row.vcpu_per_node ?? "—"}</td>
                            <td className="px-3 py-2.5 text-right text-slate-600">{row.ram_per_node ? `${row.ram_per_node}GB` : "—"}</td>
                            <td className="px-3 py-2.5 text-right font-bold text-blue-600">{formatCurrency(row.awsMo)}</td>
                            {/* GCP side */}
                            <td className="px-3 py-2.5 border-l border-slate-100">
                              <span className="px-2 py-0.5 bg-violet-50 text-violet-700 rounded font-mono font-semibold">{row.gcpRole?.gcp_instance_type ?? row.gcpRole?.instance_type ?? "—"}</span>
                            </td>
                            {(() => {
                              const gcpSpec = parseGcpSpec(row.gcpRole?.gcp_instance_type ?? row.gcpRole?.instance_type);
                              return (
                                <>
                                  <td className="px-3 py-2.5 text-right text-slate-600">{gcpSpec.vcpu ?? "—"}</td>
                                  <td className="px-3 py-2.5 text-right text-slate-600">{gcpSpec.ram ? `${gcpSpec.ram}GB` : "—"}</td>
                                </>
                              );
                            })()}
                            <td className="px-3 py-2.5 text-right font-bold text-violet-600">{row.gcpMo > 0 ? formatCurrency(row.gcpMo) : "—"}</td>
                            <td className="px-3 py-2.5 text-right">
                              {row.awsMo > 0 && row.gcpMo > 0 ? (
                                <span className={`px-2 py-0.5 font-bold rounded-full ${awsWins ? "bg-blue-100 text-blue-700" : "bg-violet-100 text-violet-700"}`}>
                                  {awsWins ? "AWS" : "GCP"} {diffStr}
                                </span>
                              ) : "—"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </motion.div>
          );
        })()}

        {/* Overview-only visual charts */}
        {activeSection === "overview" && (
        <div className="grid grid-cols-2 gap-5 mb-6">
          <motion.div initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }} transition={{ delay: 0.1 }}
            className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col">
            <p className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">Production Cost — CRM Module</p>
            <p className="text-[11px] text-slate-400 mb-3">Core infrastructure spend · AI services cost shown in AI Services tab</p>
            {categoryChartData.length > 0 ? (
              <>
                <EChartsReact
                  option={prodCategoryOption}
                  style={{ height: Math.max(160, categoryChartData.length * 40) }}
                />
                {/* Summary stats row */}
                <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-3 gap-3">
                  {[
                    {
                      label: "CRM Prod Monthly",
                      value: formatCurrency(crmProdMonthly),
                      sub: `${formatCurrency(crmProdMonthly * 12)}/yr`,
                      color: "bg-blue-50 text-blue-700 border-blue-100",
                    },
                    {
                      label: "Largest Category",
                      value: categoryChartData[0]?.[0] ?? "—",
                      sub: `${crmProdMonthly > 0 ? ((categoryChartData[0]?.[1] ?? 0) / crmProdMonthly * 100).toFixed(0) : 0}% of CRM prod`,
                      color: "bg-violet-50 text-violet-700 border-violet-100",
                    },
                    {
                      label: "Active Categories",
                      value: `${categoryChartData.length}`,
                      sub: `${categoryChartData.length} infra categories`,
                      color: "bg-emerald-50 text-emerald-700 border-emerald-100",
                    },
                  ].map((stat) => (
                    <div key={stat.label} className={`rounded-xl border p-3 ${stat.color}`}>
                      <p className="text-[10px] font-semibold uppercase tracking-wide opacity-70 mb-0.5">{stat.label}</p>
                      <p className="text-sm font-bold leading-tight truncate">{stat.value}</p>
                      <p className="text-[10px] opacity-60 mt-0.5">{stat.sub}</p>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-48 text-slate-400 text-sm">Run a new estimate to see breakdown</div>
            )}
          </motion.div>

          {/* Environment Monthly Cost — CRM Module */}
          <motion.div initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }} transition={{ delay: 0.18 }}
            className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <p className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">Environment Monthly Cost — CRM Module</p>
            <p className="text-[11px] text-slate-400 mb-3">Core infrastructure cost per environment · excludes AI services</p>
            {crmEnvBreakdown.length > 0 ? (
              <>
                <EChartsReact option={envCompareOption}
                  style={{ height: Math.max(80, crmEnvBreakdown.length * 52) }} />
                {/* Per-env detail table */}
                <div className="mt-3 pt-3 border-t border-slate-100 space-y-1.5">
                  {crmEnvBreakdown.map((env, i) => {
                    const pct = crmTotalMonthly > 0 ? (env.value / crmTotalMonthly * 100).toFixed(1) : "0";
                    return (
                      <div key={env.name} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: ENV_COLORS[i % ENV_COLORS.length] }} />
                          <span className="text-slate-600 font-semibold">{env.name}</span>
                        </div>
                        <div className="flex items-center gap-4 text-right">
                          <span className="text-slate-800 font-bold">{formatCurrency(env.value)}/mo</span>
                          <span className="text-slate-500">{formatCurrency(env.value * 12)}/yr</span>
                          <span className="text-slate-400 w-10">{pct}%</span>
                        </div>
                      </div>
                    );
                  })}
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-600">CRM Infrastructure Total</span>
                    <span className="text-sm font-bold text-blue-700">{formatCurrency(crmTotalMonthly)}/mo
                      <span className="text-xs font-normal text-slate-400 ml-1">({formatCurrency(crmTotalMonthly * 12)}/yr)</span>
                    </span>
                  </div>
                  {hasAi && (
                    <p className="text-[10px] text-violet-500 pt-1">
                      🤖 AI Services adds {formatCurrency(aiMonthly)}/mo · see AI Services tab
                    </p>
                  )}
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-40 text-slate-400 text-sm">No environment data</div>
            )}
          </motion.div>
        </div>
        )}

        {/* Infrastructure Table — Infrastructure Sizing tab ONLY */}
        {activeSection === "Infrastructure Sizing" && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm mb-6">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900">Infrastructure Sizing</h3>
            <div className="flex gap-1">
              {visibleTabs.map((tab) => (
                <button key={tab} onClick={() => setActiveEnv(tab)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${activeEnv === tab ? "text-white" : "text-slate-500 hover:bg-slate-100"}`}
                  style={activeEnv === tab ? { background: "linear-gradient(135deg, #2563eb, #1d4ed8)" } : {}}>
                  {tab}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-100">
                  {["Role", "Instance Type", "vCPU", "RAM (GB)", "Storage", "Quantity", "Monthly Cost"].map((h) => (
                    <th key={h} className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {currentInfra?.map((row, i) => (
                  <motion.tr key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }} className="table-row-hover">
                    <td className="px-5 py-3.5 text-sm font-medium text-slate-800">{row.role}</td>
                    <td className="px-5 py-3.5"><span className="px-2 py-1 bg-slate-100 text-slate-700 text-xs font-mono font-semibold rounded">{row.instance}</span></td>
                    <td className="px-5 py-3.5 text-sm text-slate-600">{row.vcpu}</td>
                    <td className="px-5 py-3.5 text-sm text-slate-600">{row.ram}</td>
                    <td className="px-5 py-3.5 text-sm text-slate-600">{row.storage}</td>
                    <td className="px-5 py-3.5 text-sm text-slate-600">{row.quantity}</td>
                    <td className="px-5 py-3.5 text-sm font-bold text-slate-900">{formatCurrency(row.cost)}</td>
                  </motion.tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-slate-200 bg-slate-50">
                  <td colSpan={6} className="px-5 py-3.5 text-sm font-bold text-slate-700">Total ({activeEnv})</td>
                  <td className="px-5 py-3.5 text-sm font-bold text-blue-600">
                    {formatCurrency(currentInfra?.reduce((sum, r) => sum + r.cost, 0) ?? 0)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
        )}

        {/* ────────── AI Services tab ─────────────────────────────────── */}
        {activeSection === "AI Services" && (() => {
          const ai5YearTCO = aiMonthly * 12 * INFLATION_FACTOR_5Y;
          const totalPct   = realProdMonthly > 0 ? ((aiMonthly / realProdMonthly) * 100).toFixed(1) : "0";
          // Year-by-year AI projection
          const aiYearlyForecast = [1,2,3,4,5].map(y => ({
            year: y, monthly: aiMonthly * Math.pow(1.04, y), annual: aiMonthly * 12 * Math.pow(1.04, y)
          }));
          // By service type
          const typeGroups: Record<string,number> = {};
          aiDisplayRows.forEach(r => { typeGroups[r.type] = (typeGroups[r.type] ?? 0) + r.monthly; });
          const typeColors: Record<string,string> = {
            "Predictive AI": "#2563eb", "Generative AI": "#7c3aed",
            "Agentic AI": "#059669", "Managed API": "#f59e0b", "AI Service": "#0891b2"
          };
          const aiProjectionOption = {
            tooltip: { trigger: "axis", backgroundColor: "#1e293b", borderColor: "#334155",
              textStyle: { color: "#f8fafc", fontSize: 12 },
              formatter: (p: {name:string;data:number}[]) => p.map(s => `Year ${s.name}: $${Math.round(s.data).toLocaleString()}/yr`).join("<br/>"),
            },
            grid: { left: "5%", right: "5%", bottom: "5%", top: "10%", containLabel: true },
            xAxis: { type: "category", data: ["Y1","Y2","Y3","Y4","Y5"],
              axisLabel: { color: "#94a3b8", fontSize: 12 }, axisLine: { lineStyle: { color: "#e2e8f0" } }, axisTick: { show: false } },
            yAxis: { type: "value",
              axisLabel: { color: "#94a3b8", fontSize: 11, formatter: (v:number) => `$${(v/1000).toFixed(0)}k` },
              splitLine: { lineStyle: { color: "#f1f5f9", type: "dashed" } }, axisLine: { show: false }, axisTick: { show: false } },
            series: [{
              name: "AI Annual Cost", type: "bar", barWidth: 40, borderRadius: [8,8,0,0],
              itemStyle: { color: { type: "linear", x:0,y:0,x2:0,y2:1,
                colorStops: [{ offset:0, color:"#7c3aed" },{ offset:1, color:"#a78bfa" }] } },
              data: aiYearlyForecast.map(y => Math.round(y.annual)),
              label: { show: true, position: "top", fontSize: 10, color: "#7c3aed",
                formatter: (p:{value:number}) => `$${(p.value/1000).toFixed(1)}k` },
            }],
          };
          return (
            <div className="space-y-5 mb-6">
              {/* KPI cards */}
              <div className="grid grid-cols-4 gap-4">
                {[
                  { label: "AI Monthly Cost",    value: formatCurrency(aiMonthly),    sub: `${totalPct}% of total production`, color: "violet" },
                  { label: "AI Annual Cost",      value: formatCurrency(aiAnnual),     sub: "Without inflation",                color: "blue" },
                  { label: "AI 5 Year TCO",       value: formatCurrency(ai5YearTCO),   sub: "With 4% annual inflation",          color: "emerald" },
                  { label: "GPU Nodes",            value: String(aiDisplayRows.filter(r => r.nodes > 0).reduce((s,r) => s + r.nodes, 0)),
                    sub: `${aiDisplayRows.filter(r=>r.nodes>0).length} services on P-series`, color: "amber" },
                ].map((kpi, i) => (
                  <motion.div key={kpi.label} initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }} transition={{ delay: i * 0.07 }}
                    className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4">
                    <p className={`text-[10px] font-bold uppercase tracking-wide mb-1 text-${kpi.color}-600`}>{kpi.label}</p>
                    <p className="text-2xl font-bold text-slate-900 mb-0.5">{kpi.value}</p>
                    <p className="text-[10px] text-slate-400">{kpi.sub}</p>
                  </motion.div>
                ))}
              </div>

              {/* Service type breakdown + projection chart */}
              <div className="grid grid-cols-5 gap-5">
                {/* By Type Summary */}
                <div className="col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                  <h3 className="text-sm font-bold text-slate-900 mb-3">Cost by AI Service Type</h3>
                  <div className="space-y-3">
                    {Object.entries(typeGroups).map(([type, cost]) => {
                      const pct = aiMonthly > 0 ? (cost / aiMonthly * 100).toFixed(0) : 0;
                      const color = typeColors[type] ?? "#64748b";
                      return (
                        <div key={type}>
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
                              <span className="text-xs font-semibold text-slate-700">{type}</span>
                            </div>
                            <div className="text-right">
                              <span className="text-xs font-bold text-slate-800">{formatCurrency(cost)}/mo</span>
                              <span className="text-[10px] text-slate-400 ml-1">({pct}%)</span>
                            </div>
                          </div>
                          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
                          </div>
                        </div>
                      );
                    })}
                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-600">Total AI Monthly</span>
                      <span className="text-sm font-bold text-violet-600">{formatCurrency(aiMonthly)}/mo</span>
                    </div>
                  </div>
                </div>
                {/* 5-year projection chart */}
                <div className="col-span-3 bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                  <h3 className="text-sm font-bold text-slate-900 mb-0.5">AI Cost Projection — 5 Years</h3>
                  <p className="text-[11px] text-slate-400 mb-3">Annual AI spend with 4% inflation · Production only</p>
                  <EChartsReact option={aiProjectionOption} style={{ height: 220 }} />
                </div>
              </div>

              {/* Per-service GPU breakdown table with sub-tabs */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">AI Services — GPU Node Breakdown</h3>
                    <p className="text-[11px] text-slate-400 mt-0.5">P-series GPU instances · Filter by service type</p>
                  </div>
                  {/* Sub-tabs: All + one per AI type */}
                  <div className="flex gap-1">
                    {["All", ...Object.keys(typeGroups)].map(tab => (
                      <button key={tab} onClick={() => setAiTypeTab(tab)}
                        className={`px-3 py-1.5 text-[10px] font-bold rounded-lg transition-all ${
                          aiTypeTab === tab ? "text-white shadow-sm" : "text-slate-500 hover:bg-slate-100"
                        }`}
                        style={aiTypeTab === tab ? { background: typeColors[tab] ?? "#2563eb" } : {}}>
                        {tab === "All" ? "All Services" : tab}
                      </button>
                    ))}
                  </div>
                </div>
                {(() => {
                  // Extract environment from role label e.g. "Minio (Production)" -> "Production"
                  const _getEnv = (label: string) => { const m = label.match(/\(([^)]+)\)$/); return m ? m[1] : "—"; };
                  const filteredRows = aiTypeTab === "All" ? aiDisplayRows : aiDisplayRows.filter(r => r.type === aiTypeTab);
                  const showEnvCol  = aiTypeTab !== "All"; // Replace TYPE column with ENV when filtered
                  const filteredTotal = filteredRows.reduce((s, r) => s + r.monthly, 0);
                  const colHeaders = ["Service Name", showEnvCol ? "Environment" : "Type", "GPU Instance", "vCPU", "RAM", "Nodes", "Monthly", "Annual", "Note"];
                  if (filteredRows.length === 0) return (
                    <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                      <span className="text-3xl mb-2">🤖</span>
                      <p className="text-sm font-medium">No {aiTypeTab} services enabled in this estimate</p>
                    </div>
                  );
                  return (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-slate-100">
                            {colHeaders.map(h => (
                              <th key={h} className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider whitespace-nowrap">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                          {filteredRows.map((row, i) => (
                            <motion.tr key={i} initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ delay: i * 0.04 }}
                              className="hover:bg-violet-50/40 transition-colors">
                              <td className="px-4 py-3.5 text-sm font-semibold text-slate-800">{row.role}</td>
                              <td className="px-4 py-3.5">
                                {showEnvCol ? (
                                  <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-[10px] font-bold rounded-full">{_getEnv(row.role)}</span>
                                ) : (
                                  <span className="px-2 py-0.5 text-[10px] font-bold rounded-full"
                                    style={{ background: (typeColors[row.type] ?? "#64748b") + "18", color: typeColors[row.type] ?? "#64748b" }}>
                                    {row.type}
                                  </span>
                                )}
                              </td>
                              <td className="px-4 py-3.5">
                                <span className="px-2 py-1 bg-violet-100 text-violet-800 text-xs font-mono font-bold rounded">{row.instance}</span>
                              </td>
                              <td className="px-4 py-3.5 text-sm text-slate-600">{row.vcpu}</td>
                              <td className="px-4 py-3.5 text-sm text-slate-600">{row.ram}</td>
                              <td className="px-4 py-3.5 text-sm text-slate-600">{row.nodes > 0 ? row.nodes : "API"}</td>
                              <td className="px-4 py-3.5 text-sm font-bold text-violet-700">{formatCurrency(row.monthly)}</td>
                              <td className="px-4 py-3.5 text-sm font-semibold text-slate-700">{formatCurrency(row.monthly * 12)}</td>
                              <td className="px-4 py-3.5 text-[10px] text-slate-400 max-w-[180px] truncate" title={row.note}>{row.note || "—"}</td>
                            </motion.tr>
                          ))}
                        </tbody>
                        <tfoot>
                          <tr className="border-t border-slate-200 bg-violet-50">
                            <td colSpan={6} className="px-4 py-3 text-sm font-bold text-slate-700">
                              {aiTypeTab === "All" ? "Total AI Services" : `${aiTypeTab} Total`}
                            </td>
                            <td className="px-4 py-3 text-sm font-bold text-violet-700">{formatCurrency(filteredTotal)}/mo</td>
                            <td className="px-4 py-3 text-sm font-bold text-violet-700">{formatCurrency(filteredTotal * 12)}/yr</td>
                            <td />
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  );
                })()}
              </div>
            </div>
          );
        })()}


        {/* ─── Cloud Services Breakdown full tab ─── */}
        {activeSection === "Cloud Services Breakdown" && (() => {
          const awsRoles2 = _coreRoles;
          const gcpSav   = (estimate as unknown as Record<string,unknown>)?.awsSavingsVsGcp as number ?? 0;
          const gcpSav2 = gcpSav; // keep for GCP comparison chart
          const PALETTE  = ["#2563eb","#7c3aed","#059669","#f59e0b","#ef4444","#0891b2","#64748b","#d946ef"];
          const inflation = (estimate as unknown as Record<string,unknown>)?.inflationForecast as
            { yearly?: { year:number; monthly_usd:number; annual_usd:number; cumulative_usd:number }[] } | undefined;

          // Compute core infrastructure metrics
          const totalNodes = awsRoles2.reduce((acc, r) => acc + Number(r.nodes || 0), 0);
          const totalVcpu = awsRoles2.reduce((acc, r) => acc + (Number(r.nodes || 0) * Number(r.vcpu_per_node || 0)), 0);
          const totalRam = awsRoles2.reduce((acc, r) => acc + (Number(r.nodes || 0) * Number(r.ram_per_node || 0)), 0);
          const totalStorage = awsRoles2.reduce((acc, r) => acc + (Number(r.nodes || 0) * Number(r.storage_per_node_gb || 0)), 0);
          
          const metricsCard = (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 flex flex-col justify-center relative overflow-hidden h-full">
              {/* Decorative background element */}
              <div className="absolute -right-6 -top-6 w-32 h-32 bg-blue-50 rounded-full blur-2xl opacity-60 pointer-events-none"></div>
              
              <p className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1 relative z-10">Core Infrastructure Capacity</p>
              <p className="text-[11px] text-slate-400 mb-6 relative z-10">Aggregated compute and storage resources for Production</p>
              
              <div className="grid grid-cols-2 gap-4 relative z-10">
                <div className="bg-gradient-to-br from-slate-50 to-white rounded-xl p-4 border border-slate-100 flex flex-col items-center justify-center text-center shadow-sm hover:shadow-md transition-shadow">
                  <span className="text-3xl font-black text-blue-600 mb-1">{totalNodes}</span>
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Total Nodes</span>
                </div>
                <div className="bg-gradient-to-br from-slate-50 to-white rounded-xl p-4 border border-slate-100 flex flex-col items-center justify-center text-center shadow-sm hover:shadow-md transition-shadow">
                  <span className="text-3xl font-black text-emerald-600 mb-1">{totalVcpu}</span>
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Total vCPU Cores</span>
                </div>
                <div className="bg-gradient-to-br from-slate-50 to-white rounded-xl p-4 border border-slate-100 flex flex-col items-center justify-center text-center shadow-sm hover:shadow-md transition-shadow">
                  <span className="text-3xl font-black text-purple-600 mb-1">
                    {totalRam > 1000 ? (totalRam/1024).toFixed(1) : totalRam}
                    <span className="text-sm font-bold text-purple-400 ml-1">{totalRam > 1000 ? 'TB' : 'GB'}</span>
                  </span>
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Total Memory</span>
                </div>
                <div className="bg-gradient-to-br from-slate-50 to-white rounded-xl p-4 border border-slate-100 flex flex-col items-center justify-center text-center shadow-sm hover:shadow-md transition-shadow">
                  <span className="text-3xl font-black text-amber-500 mb-1">
                    {totalStorage >= 1000 ? (totalStorage/1000).toFixed(1) : totalStorage}
                    <span className="text-sm font-bold text-amber-400 ml-1">{totalStorage >= 1000 ? 'TB' : 'GB'}</span>
                  </span>
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Total Storage</span>
                </div>
              </div>
            </div>
          );

          return (
            <div className="space-y-5 mb-6">
              <div className="grid grid-cols-2 gap-5">
                {/* Left Column: Cost by Category + optional metrics stack */}
                <div className="flex flex-col space-y-5">
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                    <p className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">Cost by Category</p>
                    <p className="text-[11px] text-slate-400 mb-3">CRM infrastructure · Production AWS spend</p>
                    {categoryChartData.length > 0 ? (
                      <>
                        <EChartsReact option={{
                          tooltip:{ trigger:"axis", axisPointer:{type:"shadow"}, backgroundColor:"#1e293b", borderColor:"#334155",
                            textStyle:{color:"#f8fafc",fontSize:12},
                            formatter:(p:{name:string;value:number}[])=>`<b>${p[0].name}</b><br/>$${p[0].value.toLocaleString()}/mo<br/>${crmProdMonthly>0?(p[0].value/crmProdMonthly*100).toFixed(1):0}% of prod` },
                          grid:{left:110,right:95,top:8,bottom:8,containLabel:false},
                          xAxis:{type:"value",show:false},
                          yAxis:{type:"category",data:[...categoryChartData].reverse().map(([k])=>k),
                            axisLabel:{color:"#475569",fontSize:11,fontWeight:"600"},axisLine:{show:false},axisTick:{show:false}},
                          series:[{type:"bar",barWidth:20,borderRadius:[0,6,6,0],
                            data:[...categoryChartData].reverse().map(([,v],i)=>({
                              value:Math.round(v),
                              itemStyle:{color:{type:"linear",x:0,y:0,x2:1,y2:0,
                                colorStops:[{offset:0,color:PALETTE[i%8]},{offset:1,color:PALETTE[i%8]+"bb"}]}}
                            })),
                            label:{show:true,position:"right",distance:6,fontSize:10,fontWeight:"bold",color:"#1e293b",
                              formatter:(p:{value:number})=>`$${p.value.toLocaleString()}  ${crmProdMonthly>0?(p.value/crmProdMonthly*100).toFixed(0):0}%`},
                          }],
                        }} style={{height:Math.max(120,categoryChartData.length*36)}} />
                        <div className="mt-3 pt-2 border-t border-slate-100 flex justify-between">
                          <span className="text-xs text-slate-500 font-medium">CRM Infrastructure Total</span>
                          <span className="text-xs font-bold text-slate-800">{formatCurrency(crmProdMonthly)}/mo</span>
                        </div>
                      </>
                    ) : <div className="flex items-center justify-center h-48 text-slate-400 text-sm">Run estimate first</div>}
                  </div>
                  
                  {/* When GCP is selected, the right column is tall. We fill the left column with the metrics card! */}
                  {hasGcp && metricsCard}
                </div>

                {/* Right Column: AWS vs GCP OR Infrastructure Metrics */}
                {hasGcp ? (
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 h-full">
                    <p className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">AWS vs GCP — Category Comparison</p>
                    <p className="text-[11px] text-slate-400 mb-3">Monthly spend per category (Production) · sorted by AWS cost</p>
                    {(() => {
                      const catComp = estimate?.gcpComparison?.category_comparison ?? [];
                      if (catComp.length === 0) return <div className="flex items-center justify-center h-48 text-slate-400 text-sm">Generate a new estimate to see GCP data</div>;
                      const sorted  = [...catComp].sort((a,b)=>(b.aws_monthly??0)-(a.aws_monthly??0));
                      const cats    = [...sorted].reverse().map(c=>c.category);
                      const awsVals = [...sorted].reverse().map(c=>Math.round(c.aws_monthly??0));
                      const gcpVals = [...sorted].reverse().map(c=>Math.round(c.gcp_monthly??0));
                      return (
                        <EChartsReact option={{
                          tooltip:{trigger:"axis",backgroundColor:"#1e293b",borderColor:"#334155",axisPointer:{type:"shadow"},
                            textStyle:{color:"#f8fafc",fontSize:11},
                            formatter:(p:{seriesName:string;value:number;axisValue:string}[])=>
                              `<b>${p[0].axisValue}</b><br/>`+p.map(s=>`${s.seriesName}: $${Math.round(s.value).toLocaleString()}/mo`).join("<br/>")},
                          legend:{bottom:0,textStyle:{fontSize:10,color:"#475569"},data:["AWS","GCP"]},
                          grid:{left:115,right:75,top:10,bottom:30,containLabel:false},
                          xAxis:{type:"value",axisLabel:{formatter:(v:number)=>`$${(v/1000).toFixed(0)}k`,fontSize:10,color:"#94a3b8"},splitLine:{lineStyle:{color:"#f1f5f9"}}},
                          yAxis:{type:"category",data:cats,axisLabel:{fontSize:10,color:"#475569",width:105,overflow:"truncate"},axisTick:{show:false},axisLine:{show:false}},
                          series:[
                            {name:"AWS",type:"bar",barMaxWidth:14,itemStyle:{borderRadius:[0,4,4,0],color:"#3b82f6"},
                              label:{show:true,position:"right",fontSize:9,color:"#475569",formatter:(p:{value:number})=>p.value>0?`$${Math.round(p.value).toLocaleString()}`:""},
                              data:awsVals},
                            {name:"GCP",type:"bar",barMaxWidth:14,itemStyle:{borderRadius:[0,4,4,0],color:"#8b5cf6"},
                              label:{show:true,position:"right",fontSize:9,color:"#8b5cf6",formatter:(p:{value:number})=>p.value>0?`$${Math.round(p.value).toLocaleString()}`:""},
                              data:gcpVals},
                          ],
                        }} style={{height:Math.max(260,cats.length*50)}} />
                      );
                    })()}
                  </div>
                ) : (
                  <div className="flex flex-col h-full">
                    {metricsCard}
                  </div>
                )}
              </div>

              {/* Per-role cost table — ALL environments */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
                  <p className="text-xs font-bold text-slate-700 uppercase tracking-wide">Per-Role Cost Breakdown — All Environments</p>
                  <span className="text-[10px] text-slate-400">{awsRoles2.length} services · Prod + SIT/UAT + DR</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-slate-100 bg-slate-50/60">
                        {["Role","Category","Instance","Nodes","vCPU","RAM","Storage","All-Env/mo","All-Env/yr","% Total"].map(h=>(
                          <th key={h} className="px-3 py-2.5 text-left font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap text-[10px]">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {awsRoles2.filter(r=>(r.monthly_usd??0)>0).sort((a,b)=>(b.monthly_usd??0)-(a.monthly_usd??0)).map((r,i)=>{
                        const sitRole = (envData?.preprod_sit_uat?.priced_roles??[]).find(x=>(x as any).role_key===(r as any).role_key);
                        const drRole  = (envData?.dr?.priced_roles??[]).find(x=>(x as any).role_key===(r as any).role_key);
                        const allMo   = (r.monthly_usd??0) + (sitRole?.monthly_usd??0) + (drRole?.monthly_usd??0);
                        const totalAllEnv = realProdMonthly + ppMonthly + drMonthly;
                        const pct = totalAllEnv>0 ? (allMo/totalAllEnv*100) : 0;
                        return (
                          <tr key={r.role_key??i} className="hover:bg-slate-50 transition-colors">
                            <td className="px-3 py-2.5 font-medium text-slate-700 max-w-[140px] truncate" title={r.label}>{r.label}</td>
                            <td className="px-3 py-2.5 text-slate-500 whitespace-nowrap">{r.category ?? "—"}</td>
                            <td className="px-3 py-2.5"><span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded font-mono font-semibold">{r.instance_type ?? "—"}</span></td>
                            <td className="px-3 py-2.5 text-center text-slate-600">{r.nodes ?? "—"}</td>
                            <td className="px-3 py-2.5 text-center text-slate-600">{r.vcpu_per_node ?? "—"}</td>
                            <td className="px-3 py-2.5 text-slate-600">{r.ram_per_node ? `${r.ram_per_node}GB` : "—"}</td>
                            <td className="px-3 py-2.5 text-slate-600">{r.storage_per_node_gb ? `${r.storage_per_node_gb}GB` : "—"}</td>
                            <td className="px-3 py-2.5 font-bold text-slate-800">{formatCurrency(allMo)}</td>
                            <td className="px-3 py-2.5 text-slate-600">{formatCurrency(allMo*12)}</td>
                            <td className="px-3 py-2.5">
                              <div className="flex items-center gap-2">
                                <div className="w-14 bg-slate-100 rounded-full h-1.5">
                                  <div className="h-1.5 rounded-full bg-blue-500" style={{width:`${Math.min(pct,100)}%`}} />
                                </div>
                                <span className="text-slate-500">{pct.toFixed(1)}%</span>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot>
                      <tr className="border-t-2 border-slate-200 bg-slate-50">
                        <td colSpan={7} className="px-3 py-3 text-xs font-bold text-slate-700">Total — All Environments</td>
                        <td className="px-3 py-3 text-xs font-bold text-slate-900">{formatCurrency(realProdMonthly+ppMonthly+drMonthly)}</td>
                        <td className="px-3 py-3 text-xs font-bold text-slate-900">{formatCurrency((realProdMonthly+ppMonthly+drMonthly)*12)}</td>
                        <td className="px-3 py-3 text-xs font-bold text-slate-500">100%</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              {/* 5-year projection */}
              {inflation?.yearly && inflation.yearly.length > 0 && (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                  <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50">
                    <p className="text-xs font-bold text-slate-700 uppercase tracking-wide">5-Year AWS Cost Projection</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">4% annual inflation applied · Production only</p>
                  </div>
                  <div className="grid grid-cols-5 divide-x divide-slate-100">
                    {inflation.yearly.map(y=>(
                      <div key={y.year} className="p-4 text-center">
                        <p className="text-[10px] font-bold text-slate-400 uppercase mb-2">Year {y.year}</p>
                        <p className="text-base font-bold text-slate-800">{formatCurrency(y.monthly_usd)}/mo</p>
                        <p className="text-xs text-slate-500 mt-0.5">{formatCurrency(y.annual_usd)}/yr</p>
                        <p className="text-[10px] text-slate-400 mt-1">Cum. {formatCurrency(y.cumulative_usd)}</p>
                        <div className="mt-2 h-1 bg-slate-100 rounded-full">
                          <div className="h-1 rounded-full bg-blue-500" style={{width:`${(y.monthly_usd/((inflation.yearly??[])[4]?.monthly_usd??1))*100}%`}} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* AWS vs GCP savings summary + GCP roles table — only when GCP selected */}
              {hasGcp && (estimate?.gcpComparison?.category_comparison ?? []).length > 0 && (() => {
                const catComp = estimate?.gcpComparison?.category_comparison ?? [];
                const gcpRoles = estimate?.gcpPricedRoles ?? [];
                const gcpTotal = gcpRoles.reduce((s,r)=>s+((r as Record<string,unknown>).monthly_usd as number??0),0);
                const totalSavPct = gcpTotal>0 ? ((realProdMonthly-gcpTotal)/gcpTotal*100) : null;
                return (
                  <>
                    {/* Savings summary row */}
                    <div className="grid grid-cols-3 gap-4">
                      {[
                        {label:"AWS Total (Prod)",  val:formatCurrency(realProdMonthly),    sub:"/month",        color:"blue"},
                        {label:"GCP Equivalent",     val:gcpTotal>0?formatCurrency(gcpTotal):"—", sub:"/month",  color:"violet"},
                        {label:"AWS Savings vs GCP", val:totalSavPct!==null?`${totalSavPct>0?"+":""}${totalSavPct.toFixed(1)}%`:"—",
                          sub:gcpTotal>0?`$${Math.abs(Math.round(realProdMonthly-gcpTotal)).toLocaleString()}/mo ${realProdMonthly<gcpTotal?"cheaper":"more expensive"}`:"",
                          color:totalSavPct!==null&&totalSavPct<0?"emerald":"amber"},
                      ].map(k=>(
                        <div key={k.label} className={`bg-${k.color}-50 border border-${k.color}-100 rounded-2xl p-4`}>
                          <p className={`text-[10px] font-bold text-${k.color}-600 uppercase tracking-wide mb-1`}>{k.label}</p>
                          <p className={`text-xl font-bold text-${k.color}-700`}>{k.val}</p>
                          <p className={`text-[10px] text-${k.color}-400 mt-0.5`}>{k.sub}</p>
                        </div>
                      ))}
                    </div>

                    {/* GCP per-role table */}
                    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                      <div className="px-5 py-3.5 border-b border-slate-100 bg-violet-50 flex items-center justify-between">
                        <p className="text-xs font-bold text-violet-700 uppercase tracking-wide">GCP Equivalent — Per-Role Breakdown</p>
                        <span className="text-[10px] text-violet-400">{gcpRoles.length} services · Production</span>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-b border-slate-100 bg-violet-50/40">
                              {["Role","Category","GCP Instance","Nodes","vCPU","RAM","Monthly","Annual","vs AWS"].map(h=>(
                                <th key={h} className="px-4 py-2.5 text-left font-semibold text-violet-500 uppercase tracking-wide whitespace-nowrap text-[10px]">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-50">
                            {gcpRoles.filter(r=>((r as Record<string,unknown>).monthly_usd as number??0)>0)
                              .sort((a,b)=>((b as Record<string,unknown>).monthly_usd as number??0)-((a as Record<string,unknown>).monthly_usd as number??0))
                              .map((r,i)=>{
                                const gcpMo = (r as Record<string,unknown>).monthly_usd as number ?? 0;
                                // find matching AWS role for comparison
                                const awsR  = (estimate?.pricedRoles??[]).find(x=>x.role_key===r.role_key);
                                const awsMo = awsR?.monthly_usd ?? 0;
                                const diff  = awsMo>0&&gcpMo>0 ? ((awsMo-gcpMo)/awsMo*100) : null;
                                return (
                                  <tr key={(r.role_key??i)} className="hover:bg-violet-50/30 transition-colors">
                                    <td className="px-4 py-2.5 font-medium text-slate-700 max-w-[160px] truncate" title={r.label}>{r.label}</td>
                                    <td className="px-4 py-2.5 text-slate-500">{r.category??"—"}</td>
                                    <td className="px-4 py-2.5"><span className="px-2 py-0.5 bg-violet-50 text-violet-700 rounded font-mono font-semibold">{((r as Record<string,unknown>).gcp_instance_type as string) ?? r.instance_type ?? "—"}</span></td>
                                    <td className="px-4 py-2.5 text-center text-slate-600">{r.nodes??"—"}</td>
                                    <td className="px-4 py-2.5 text-center text-slate-600">{r.vcpu_per_node??"—"}</td>
                                    <td className="px-4 py-2.5 text-slate-600">{r.ram_per_node?`${r.ram_per_node}GB`:"—"}</td>
                                    <td className="px-4 py-2.5 font-bold text-violet-700">{formatCurrency(gcpMo)}</td>
                                    <td className="px-4 py-2.5 text-slate-600">{formatCurrency(gcpMo*12)}</td>
                                    <td className="px-4 py-2.5">
                                      {diff!==null ? (
                                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${diff>0?"bg-emerald-100 text-emerald-700":"bg-red-100 text-red-600"}`}>
                                          {diff>0?"+":""}{diff.toFixed(1)}% AWS saves
                                        </span>
                                      ) : "—"}
                                    </td>
                                  </tr>
                                );
                            })}
                          </tbody>
                          <tfoot>
                            <tr className="border-t-2 border-violet-100 bg-violet-50/40">
                              <td colSpan={6} className="px-4 py-3 text-xs font-bold text-violet-700">GCP Total Production</td>
                              <td className="px-4 py-3 text-xs font-bold text-violet-700">{formatCurrency(gcpTotal)}</td>
                              <td className="px-4 py-3 text-xs font-bold text-violet-700">{formatCurrency(gcpTotal*12)}</td>
                              <td className="px-4 py-3 text-xs font-bold text-slate-500">
                                {totalSavPct!==null&&<span className={totalSavPct>0?"text-emerald-600":"text-red-500"}>{totalSavPct>0?"+":""}{totalSavPct.toFixed(1)}% AWS</span>}
                              </td>
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                    </div>
                  </>
                );
              })()}

            </div>
          );
        })()}

        {/* Bottom-left: AWS Services pie — Overview ONLY */}
        {activeSection === "overview" && (
        <div className="grid grid-cols-3 gap-5 mb-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <p className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">AWS Services Breakdown</p>
            <p className="text-[11px] text-slate-400 mb-3">Production cost by service category</p>
            {categoryChartData.length > 0 ? (
              <>
                <EChartsReact
                  option={{
                    tooltip: {
                      trigger: "item",
                      backgroundColor: "#1e293b", borderColor: "#334155",
                      textStyle: { color: "#f8fafc", fontSize: 12 },
                      formatter: (p: { name: string; value: number; percent: number }) =>
                        `<b>${p.name}</b><br/>$${p.value.toLocaleString()}/mo<br/>${p.percent.toFixed(1)}% of total`,
                    },
                    graphic: [{
                      type: "text", left: "center", top: "36%",
                      style: { text: `$${Math.round(realProdMonthly).toLocaleString()}`, fontSize: 17, fontWeight: "bold", fill: "#1e293b", textAlign: "center" },
                    }, {
                      type: "text", left: "center", top: "46%",
                      style: { text: "Prod/mo", fontSize: 10, fill: "#94a3b8", textAlign: "center" },
                    }],
                    series: [{
                      type: "pie", radius: ["50%", "72%"], center: ["50%", "44%"],
                      padAngle: 3,
                      itemStyle: { borderRadius: 8, borderColor: "#fff", borderWidth: 2 },
                      label: {
                        show: true, position: "outside", fontSize: 10, color: "#64748b",
                        formatter: (p: { name: string; percent: number }) =>
                          `${p.percent.toFixed(0)}%`,
                      },
                      emphasis: { label: { fontSize: 12, fontWeight: "bold" } },
                      data: categoryChartData.map(([name, value], i) => ({
                        name, value: Math.round(value),
                        itemStyle: { color: ["#2563eb","#7c3aed","#059669","#f59e0b","#ef4444","#0891b2","#64748b"][i % 7] },
                      })),
                    }],
                  }}
                  style={{ height: 200 }}
                />
                <div className="mt-2 space-y-1.5 border-t border-slate-100 pt-2">
                  {categoryChartData.map(([cat, val], i) => {
                    const pct = realProdMonthly > 0 ? (val / realProdMonthly * 100).toFixed(1) : "0";
                    return (
                      <div key={cat} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full flex-shrink-0"
                            style={{ background: ["#2563eb","#7c3aed","#059669","#f59e0b","#ef4444","#0891b2","#64748b"][i % 7] }} />
                          <span className="text-slate-600">{cat}</span>
                        </div>
                        <div className="text-right">
                          <span className="font-bold text-slate-800">{formatCurrency(val)}</span>
                          <span className="text-slate-400 ml-1">({pct}%)</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-48 text-slate-400 text-sm">Run a new estimate to see breakdown</div>
            )}
          </div>

          {/* AI Insights panel — ONLY when Overview (sidebar) or AI Insights tab (full width) */}
          {(activeSection === "overview") && (
          <div className="col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <div className="flex items-center gap-2 mb-4">
              <Lightbulb className="w-4 h-4 text-amber-500" />
              <h3 className="text-sm font-bold text-slate-900">AI Recommendations</h3>
              <span className="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">Live</span>
            </div>
            <div className="space-y-3">
              {aiRecs.map((rec, i) => (
                <motion.div key={i} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                  className={`flex gap-3 p-3 rounded-xl border ${
                    rec.type === "warning" ? "bg-amber-50 border-amber-200" :
                    rec.type === "tip"     ? "bg-blue-50 border-blue-200" : "bg-violet-50 border-violet-200"}`}>
                  {rec.type === "warning" && <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />}
                  {rec.type === "tip"     && <TrendingDown className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />}
                  {rec.type === "info"    && <Info className="w-4 h-4 text-violet-500 flex-shrink-0 mt-0.5" />}
                  <div>
                    <p className="text-xs font-bold text-slate-800 mb-0.5">{rec.title}</p>
                    <p className="text-xs text-slate-600">{rec.desc}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
          )}
        </div>
        )}

        {/* AI Insights full-width tab */}
        {activeSection === "AI Insights" && (
        <div className="grid grid-cols-1 gap-5">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-center gap-2 mb-4">
              <Lightbulb className="w-5 h-5 text-amber-500" />
              <h3 className="text-base font-bold text-slate-900">AI Recommendations</h3>
              <span className="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full ml-1">Generated from your estimate</span>
            </div>
            <div className="grid grid-cols-2 gap-4 mb-6">
              {aiRecs.map((rec, i) => (
                <motion.div key={i} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                  className={`flex gap-3 p-4 rounded-xl border ${
                    rec.type === "warning" ? "bg-amber-50 border-amber-200" :
                    rec.type === "tip"     ? "bg-blue-50 border-blue-200" : "bg-violet-50 border-violet-200"}`}>
                  {rec.type === "warning" && <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />}
                  {rec.type === "tip"     && <TrendingDown className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />}
                  {rec.type === "info"    && <Info className="w-4 h-4 text-violet-500 flex-shrink-0 mt-0.5" />}
                  <div>
                    <p className="text-xs font-bold text-slate-800 mb-0.5">{rec.title}</p>
                    <p className="text-xs text-slate-600">{rec.desc}</p>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Download Center */}
            <div className="border-t border-slate-100 pt-5">
              <h4 className="text-xs font-bold text-slate-700 mb-3">Download Center</h4>
              {(() => {
                const providers = estimate?.cloudProviders ?? ["AWS"];
                const hasAws = providers.includes("AWS");
                const hasGcp = providers.includes("GCP");
                const token = typeof window !== "undefined" ? localStorage.getItem("businessnext_token") : "";
                const open = (type: string) => {
                  if (estimateId) window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/estimates/${estimateId}/files/${type}?token=${token}`, "_blank");
                };
                const allFiles = [
                  ...(hasAws ? [
                    { icon: FileSpreadsheet, label: "AWS Sizing",      ext: ".xlsx", color: "emerald", type: "sizing"           },
                    { icon: FileSpreadsheet, label: "AWS Pricing",     ext: ".xlsx", color: "blue",    type: "pricing"          },
                  ] : []),
                  ...(hasGcp ? [
                    { icon: FileSpreadsheet, label: "GCP Sizing",      ext: ".xlsx", color: "violet",  type: "gcp-sizing"       },
                    { icon: FileSpreadsheet, label: "GCP Pricing",     ext: ".xlsx", color: "violet",  type: "gcp-pricing"      },
                  ] : []),
                  ...(hasAi ? [
                    { icon: FileSpreadsheet, label: "AI Services",     ext: ".xlsx", color: "purple",  type: "ai-sizing"        },
                  ] : []),
                  { icon: FileSpreadsheet, label: "Updated Estimate",  ext: ".xlsx", color: "amber",   type: "updated-estimate" },
                  { icon: FileText,        label: "PDF Report",        ext: ".pdf",  color: "red",     type: "pdf"              },
                ];
                const colorMap: Record<string,string> = {
                  emerald: "border-emerald-200 hover:border-emerald-400 hover:bg-emerald-50",
                  blue:    "border-blue-200 hover:border-blue-400 hover:bg-blue-50",
                  violet:  "border-violet-200 hover:border-violet-400 hover:bg-violet-50",
                  purple:  "border-purple-200 hover:border-purple-400 hover:bg-purple-50",
                  amber:   "border-amber-200 hover:border-amber-400 hover:bg-amber-50",
                  red:     "border-red-200 hover:border-red-400 hover:bg-red-50",
                };
                const iconColorMap: Record<string,string> = {
                  emerald: "text-emerald-500", blue: "text-blue-500",
                  violet: "text-violet-500", purple: "text-purple-600", amber: "text-amber-500", red: "text-red-500",
                };
                return (
                  <>
                    {/* Provider/module badges */}
                    <div className="flex gap-2 mb-3 flex-wrap">
                      {hasAws && <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full text-[10px] font-bold">🟧 AWS Reports</span>}
                      {hasGcp && <span className="px-2 py-0.5 bg-violet-100 text-violet-700 rounded-full text-[10px] font-bold">🟣 GCP Reports</span>}
                      {hasAi  && <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-[10px] font-bold">🤖 AI Services</span>}
                    </div>
                    <div className={`grid gap-3 ${allFiles.length > 4 ? "grid-cols-3" : "grid-cols-4"}`}>
                      {allFiles.map((f) => (
                        <motion.button key={f.label} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                          disabled={!estimateId}
                          onClick={() => open(f.type)}
                          className={`flex items-center gap-2 p-3 rounded-xl border-2 border-dashed transition-all text-left ${colorMap[f.color]} disabled:opacity-40 disabled:cursor-not-allowed`}>
                          <f.icon className={`w-4 h-4 flex-shrink-0 ${iconColorMap[f.color]}`} />
                          <div>
                            <p className="text-xs font-semibold text-slate-700 leading-tight">{f.label}</p>
                            <p className="text-xs text-slate-400">{f.ext}</p>
                          </div>
                        </motion.button>
                      ))}
                    </div>
                    <motion.button
                      disabled={!estimateId}
                      whileHover={{ scale: estimateId ? 1.01 : 1 }}
                      onClick={() => { if (estimateId) { const t = localStorage.getItem("businessnext_token"); window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/estimates/${estimateId}/download-all?token=${t}`, "_blank"); }}}
                      className="mt-3 w-full flex items-center justify-center gap-2 py-2.5 text-sm font-bold text-white rounded-xl disabled:opacity-40 disabled:cursor-not-allowed"
                      style={{ background: "linear-gradient(135deg, #2563eb, #1d4ed8)" }}>
                      <Download className="w-4 h-4" /> Download All (ZIP)
                    </motion.button>
                    {!estimateId && <p className="text-xs text-slate-400 mt-2 text-center">Navigate from an estimate to enable downloads</p>}
                  </>
                );
              })()}
            </div>
          </div>
        </div>
        )}
      </div>
      <AICopilot
        estimateContext={estimate ? {
          estimateId:     estimate.id,
          customerName:   estimate.customerName,
          version:        estimate.version,
          awsMonthlyCost: awsMonthlyCost,
          gcpMonthlyCost: gcpMonthlyCost,
          aws5YearTCO:    aws5YearTCO,
          clientMode:     estimate.clientMode,
          dbType:         estimate.dbType,
          cloudProviders: estimate.cloudProviders,
          environments:   estimate.environments as Record<string, any>,
          metrics:        estimate.metrics as Record<string, any>,
        } : undefined}
      />
    </AppShell>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={
      <AppShell breadcrumbs={[{ label: "Results" }]}>
        <div className="flex items-center justify-center py-32 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mr-3" />
          <span className="text-sm">Loading...</span>
        </div>
      </AppShell>
    }>
      <ResultsContent />
    </Suspense>
  );
}
