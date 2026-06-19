"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  CheckCircle, User, Cpu, Database, Globe, DollarSign,
  FileText, ChevronRight, ChevronLeft, Save, Loader2,
  Users, Zap, BarChart2, Smartphone, Cloud, Server,
} from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import AICopilot from "@/components/AICopilot";
import { formatCurrency } from "@/lib/utils";
import { getPlatformSettings } from "@/lib/platformSettings";

const STEPS = [
  { id: 1, label: "Customer", icon: User },
  { id: 2, label: "Application", icon: Cpu },
  { id: 3, label: "Database", icon: Database },
  { id: 4, label: "Regions", icon: Globe },
  { id: 5, label: "Financials", icon: DollarSign },
  { id: 6, label: "Review", icon: FileText },
];

const MODULES = ["CRM", "Analytics", "AI"];
// All AWS regions (matching aws_machine_catalog.py AWS_REGIONS)
const AWS_REGIONS = [
  // Americas
  "us-east-1 (N. Virginia)", "us-east-2 (Ohio)", "us-west-1 (N. California)",
  "us-west-2 (Oregon)", "ca-central-1 (Canada Central)", "ca-west-1 (Canada Calgary)",
  "sa-east-1 (São Paulo)",
  // Europe
  "eu-central-1 (Frankfurt)", "eu-central-2 (Zurich)", "eu-west-1 (Ireland)",
  "eu-west-2 (London)", "eu-west-3 (Paris)", "eu-north-1 (Stockholm)",
  "eu-south-1 (Milan)", "eu-south-2 (Spain)",
  // Asia Pacific
  "ap-south-1 (Mumbai)", "ap-south-2 (Hyderabad)", "ap-northeast-1 (Tokyo)",
  "ap-northeast-2 (Seoul)", "ap-northeast-3 (Osaka)", "ap-southeast-1 (Singapore)",
  "ap-southeast-2 (Sydney)", "ap-southeast-3 (Jakarta)", "ap-southeast-4 (Melbourne)",
  "ap-southeast-5 (Malaysia)", "ap-east-1 (Hong Kong)",
  // Middle East & Africa
  "me-south-1 (Bahrain)", "me-central-1 (UAE)", "af-south-1 (Cape Town)",
  "il-central-1 (Tel Aviv)",
];
// All GCP regions (matching gcp_pricer.py GCP_REGIONS)
const GCP_REGIONS = [
  // Americas
  "us-central1 (Iowa)", "us-east1 (South Carolina)", "us-east4 (N. Virginia)",
  "us-east5 (Columbus)", "us-south1 (Dallas)", "us-west1 (Oregon)",
  "us-west2 (Los Angeles)", "us-west3 (Salt Lake City)", "us-west4 (Las Vegas)",
  "northamerica-northeast1 (Montréal)", "northamerica-northeast2 (Toronto)",
  "northamerica-south1 (Mexico)", "southamerica-east1 (São Paulo)",
  "southamerica-west1 (Santiago)",
  // Europe
  "europe-west1 (Belgium)", "europe-west2 (London)", "europe-west3 (Frankfurt)",
  "europe-west4 (Netherlands)", "europe-west6 (Zurich)", "europe-west8 (Milan)",
  "europe-west9 (Paris)", "europe-west10 (Berlin)", "europe-west12 (Turin)",
  "europe-central2 (Warsaw)", "europe-north1 (Finland)", "europe-north2 (Stockholm)",
  "europe-southwest1 (Madrid)",
  // Asia Pacific
  "asia-south1 (Mumbai)", "asia-south2 (Delhi)", "asia-east1 (Taiwan)",
  "asia-east2 (Hong Kong)", "asia-southeast1 (Singapore)", "asia-southeast2 (Jakarta)",
  "asia-southeast3 (Bangkok)", "asia-northeast1 (Tokyo)", "asia-northeast2 (Osaka)",
  "asia-northeast3 (Seoul)", "australia-southeast1 (Sydney)",
  "australia-southeast2 (Melbourne)",
  // Middle East & Africa
  "me-west1 (Tel Aviv)", "me-central1 (Doha)", "me-central2 (Dammam)",
  "af-south1 (Johannesburg)",
];
const ENVIRONMENTS = ["SIT", "UAT", "DR", "Preprod"];


function EstimatorWizardPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [step, setStep] = useState(1);
  const [autoSaved, setAutoSaved] = useState("Just now");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState(0);

  // Pre-fill customer name from URL ?clientName= param
  const urlClientName = searchParams.get("clientName") ?? "";

  const [form, setForm] = useState({
    customerName: urlClientName,
    estimateLabel: "",    // optional short description / label for this estimate
    deployment: "SaaS",
    namedUsers: 15500,
    namedUsersYoy: 5,
    concurrentUsers: 4650,
    concurrentUsersYoy: 5,
    concurrentMobileUsers: 0,
    concurrentMobileUsersYoy: 5,
    totalCustomers: 25786541,
    totalCustomersYoy: 10,
    numberOfLeads: 10700000,
    numberOfLeadsYoy: 10,
    serviceRequests: 20000,
    serviceRequestsYoy: 5,
    modules: ["CRM", "Analytics", "AI"],
    database: "PostgreSQL",
    clickhouse: true,
    aiServices: true,
    redis: true,
    predictiveAi: true,
    predictiveEnvs: ["prod"],
    genai: true,
    genaiTokens: 5000,
    genaiEnvs: ["prod"],
    agenticAi: false,
    agenticTasks: 1000,
    agenticEnvs: ["prod"],
    docsPerCustomer: 2,
    docsPerLead: 2,
    docsPerCase: 1,
    actsPerCustomer: 2,
    actsPerLead: 2,
    actsPerCase: 4,
    pdfPerUser: 1,
    docSizeMb: 0.25,
    perfTestingCost: 5000,
    migrationCost: 5000,
    managedSvcCost: 1000,
    awsRegion: "ap-south-1 (Mumbai)",
    gcpRegion: "asia-south1 (Mumbai)",
    environments: ["SIT", "UAT", "DR"],
    drScale: 100,
    discountPercent: 10,   // overridden by platform settings on mount
    inflationPercent: 5,   // overridden by platform settings on mount
    contractDuration: "3 Year",
    cloudProviders: ["AWS"] as string[],
  });

  // Load platform-level defaults (set by admin in Settings)
  useEffect(() => {
    if (recalculateId) return; // recalculate flow sets its own values
    const ps = getPlatformSettings();
    setForm((f) => ({
      ...f,
      discountPercent: ps.defaultDiscount,
      inflationPercent: ps.defaultInflation,
    }));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const recalculateId = searchParams.get("recalculate");
  useEffect(() => {
    if (!recalculateId) return;
    import("@/lib/api").then(({ estimatesApi }) => {
      estimatesApi.get(recalculateId)
        .then((data) => {
          const m = (data.metrics || {}) as Record<string, unknown>;
          if (!m || Object.keys(m).length === 0) return;

          // Map every snake_case key from the backend to the wizard form's camelCase shape
          const patch: Partial<typeof form> = {};

          const num  = (k: string, fallback?: number) => (m[k] != null ? Number(m[k]) : fallback) as number;
          const bool = (k: string, fallback?: boolean) => (m[k] != null ? Boolean(m[k]) : fallback) as boolean;
          const str  = (k: string, fallback?: string) => (m[k] != null ? String(m[k]) : fallback) as string;
          const arr  = (k: string, fallback?: string[]) => (Array.isArray(m[k]) ? (m[k] as string[]) : fallback) as string[];

          // Identity
          if (data.customerName)              patch.customerName          = data.customerName;
          if (data.clientMode)                patch.deployment            = data.clientMode === "onprem" ? "On-Premise" : "SaaS";
          if (data.dbType)                    patch.database              = data.dbType;

          // User counts
          if (m["total_named_users"])         patch.namedUsers            = num("total_named_users");
          if (m["concurrent_users"])          patch.concurrentUsers       = num("concurrent_users");
          if (m["mobile_users"])              patch.concurrentMobileUsers = num("mobile_users");
          if (m["total_customers"])           patch.totalCustomers        = num("total_customers");
          if (m["number_of_leads"])           patch.numberOfLeads         = num("number_of_leads");
          if (m["service_requests"])          patch.serviceRequests       = num("service_requests");

          // YoY growth
          if (m["named_users_yoy"])               patch.namedUsersYoy            = num("named_users_yoy");
          if (m["concurrent_users_yoy"])          patch.concurrentUsersYoy       = num("concurrent_users_yoy");
          if (m["concurrent_mobile_users_yoy"])   patch.concurrentMobileUsersYoy = num("concurrent_mobile_users_yoy");
          if (m["total_customers_yoy"])           patch.totalCustomersYoy        = num("total_customers_yoy");
          if (m["number_of_leads_yoy"])           patch.numberOfLeadsYoy         = num("number_of_leads_yoy");
          if (m["service_requests_yoy"])          patch.serviceRequestsYoy       = num("service_requests_yoy");

          // Modules & environments
          if (m["modules"])                   patch.modules               = arr("modules");
          if (m["environments"])              patch.environments          = arr("environments");
          if (m["dr_scale"] != null)          patch.drScale               = num("dr_scale");

          // Advanced services
          if (m["clickhouse_enabled"] != null)    patch.clickhouse        = bool("clickhouse_enabled");
          if (m["ai_services_enabled"] != null)   patch.aiServices        = bool("ai_services_enabled");

          // AI workloads
          if (m["predictive_ai"] != null)     patch.predictiveAi          = bool("predictive_ai");
          if (m["predictive_envs"])           patch.predictiveEnvs        = arr("predictive_envs");
          if (m["genai_ai"] != null)          patch.genai                 = bool("genai_ai");
          if (m["genai_tokens"] != null)      patch.genaiTokens           = num("genai_tokens");
          if (m["genai_envs"])                patch.genaiEnvs             = arr("genai_envs");
          if (m["agentic_ai"] != null)        patch.agenticAi             = bool("agentic_ai");
          if (m["agentic_tasks"] != null)     patch.agenticTasks          = num("agentic_tasks");
          if (m["agentic_envs"])              patch.agenticEnvs           = arr("agentic_envs");

          // Sizing assumptions
          if (m["docs_per_customer"] != null) patch.docsPerCustomer       = num("docs_per_customer");
          if (m["docs_per_lead"] != null)     patch.docsPerLead           = num("docs_per_lead");
          if (m["docs_per_case"] != null)     patch.docsPerCase           = num("docs_per_case");
          if (m["acts_per_customer"] != null) patch.actsPerCustomer       = num("acts_per_customer");
          if (m["acts_per_lead"] != null)     patch.actsPerLead           = num("acts_per_lead");
          if (m["acts_per_case"] != null)     patch.actsPerCase           = num("acts_per_case");
          if (m["pdf_per_user"] != null)      patch.pdfPerUser            = num("pdf_per_user");
          if (m["doc_size_mb"] != null)       patch.docSizeMb             = num("doc_size_mb");

          // Financial
          if (m["discount_percent"] != null)  patch.discountPercent       = num("discount_percent");
          if (m["inflation_percent"] != null) patch.inflationPercent      = num("inflation_percent");
          if (m["contract_duration"])         patch.contractDuration      = str("contract_duration");
          if (m["aws_region"])                patch.awsRegion             = str("aws_region");

          // One-time costs
          if (m["one_time_perf_testing"] != null) patch.perfTestingCost   = num("one_time_perf_testing");
          if (m["one_time_migration"] != null)    patch.migrationCost     = num("one_time_migration");
          if (m["one_time_managed_svc"] != null)  patch.managedSvcCost    = num("one_time_managed_svc");

          setForm((f) => ({ ...f, ...patch }));
        })
        .catch((err) => console.error("Failed to load estimate for recalculation:", err));
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recalculateId]);

  const estimatedCost = Math.round(
    (form.concurrentUsers * 2.4 + 1800 + form.environments.length * 1200) *
    (1 - form.discountPercent / 100)
  );

  const triggerAutoSave = () => setAutoSaved(new Date().toLocaleTimeString());

  const handleChange = (key: string, value: unknown) => {
    setForm((f) => {
      const newForm = { ...f, [key]: value };
      if (key === "deployment" && value === "SaaS") {
        newForm.database = "PostgreSQL";
      }
      return newForm;
    });
    triggerAutoSave();
  };

  const toggleModule = (m: string) => {
    setForm((f) => {
      const isSelected = f.modules.includes(m);
      const newModules = isSelected ? f.modules.filter((x) => x !== m) : [...f.modules, m];
      
      const newForm = { ...f, modules: newModules };
      
      if (m === "Analytics") {
        newForm.clickhouse = !isSelected;
      }
      if (m === "AI") {
        newForm.aiServices = !isSelected;
      }
      
      return newForm;
    });
    triggerAutoSave();
  };

  const toggleEnv = (e: string) => {
    setForm((f) => ({
      ...f,
      environments: f.environments.includes(e) ? f.environments.filter((x) => x !== e) : [...f.environments, e],
    }));
    triggerAutoSave();
  };

  const GENERATION_STEPS = [
    "Recalculating Sizing Template…",
    "Extracting Infrastructure Metrics…",
    "Distributing Nodes & AI Workloads…",
    "Fetching AWS Prices…",
    "Pricing Environments (Pre-Prod / DR)…",
    "Generating Excel & PDF Reports…",
    "Saving Estimate…",
  ];

  const [generateError, setGenerateError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerateError(null);

    // Animate through steps while the API call runs
    const stepInterval = setInterval(() => {
      setGenerationStep((prev) =>
        prev < GENERATION_STEPS.length - 1 ? prev + 1 : prev
      );
    }, 2000);

    try {
      const token = localStorage.getItem("businessnext_token");
      const clientId = searchParams.get("clientId") ?? undefined;

      // Derive clean AWS region code (strip label, e.g. "ap-south-1 (Mumbai)" → "ap-south-1")
      const awsRegionCode = form.awsRegion.split(" ")[0];

      const payload = {
        clientId:               clientId ?? null,
        clientName:             form.customerName || "Bank",
        deployment:             form.deployment,
        database:               form.database,

        namedUsers:             form.namedUsers,
        concurrentUsers:        form.concurrentUsers,
        concurrentMobileUsers:  form.concurrentMobileUsers,
        totalCustomers:         form.totalCustomers,
        numberOfLeads:          form.numberOfLeads,
        serviceRequests:        form.serviceRequests,

        namedUsersYoy:              form.namedUsersYoy,
        concurrentUsersYoy:         form.concurrentUsersYoy,
        concurrentMobileUsersYoy:   form.concurrentMobileUsersYoy,
        totalCustomersYoy:          form.totalCustomersYoy,
        numberOfLeadsYoy:           form.numberOfLeadsYoy,
        serviceRequestsYoy:         form.serviceRequestsYoy,

        modules:                form.modules,
        environments:           form.environments,
        drScale:                form.drScale,

        clickhouseEnabled:      form.clickhouse && form.modules.includes("Analytics"),
        aiServicesEnabled:      form.aiServices && form.modules.includes("AI"),

        predictiveAi:           form.predictiveAi,
        predictiveTokens:       100000,
        predictiveEnvs:         form.predictiveEnvs,
        genaiAi:                form.genai,
        genaiTokens:            form.genaiTokens,
        genaiEnvs:              form.genaiEnvs,
        agenticAi:              form.agenticAi,
        agenticTasks:           form.agenticTasks,
        agenticEnvs:            form.agenticEnvs,
        bedrockMonthly:         3000.0,

        docsPerCustomer:        form.docsPerCustomer,
        docsPerLead:            form.docsPerLead,
        docsPerCase:            form.docsPerCase,
        actsPerCustomer:        form.actsPerCustomer,
        actsPerLead:            form.actsPerLead,
        actsPerCase:            form.actsPerCase,
        pdfPerUser:             form.pdfPerUser,
        docSizeMb:              form.docSizeMb,

        discountPercent:        form.discountPercent,
        inflationPercent:       form.inflationPercent,
        contractDuration:       form.contractDuration,
        awsRegion:              awsRegionCode,
        cloudProviders:         form.deployment === "SaaS" ? form.cloudProviders : ["AWS"],

        perfTestingCost:        form.perfTestingCost,
        migrationCost:          form.migrationCost,
        managedSvcCost:         form.managedSvcCost,
        estimateNotes:          form.estimateLabel || "",
      };

      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiBase}/api/generate-estimate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      clearInterval(stepInterval);
      setGenerationStep(GENERATION_STEPS.length - 1);

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      // Small pause so the user sees the final step
      await new Promise((r) => setTimeout(r, 600));

      // Redirect to results page with estimateId
      router.push(`/results?id=${data.estimateId}&monthly=${data.grandMonthly}&annual=${data.grandAnnual}${clientId ? `&clientId=${clientId}` : ''}`);
    } catch (err: unknown) {
      clearInterval(stepInterval);
      setGenerateError(err instanceof Error ? err.message : String(err));
      setIsGenerating(false);
      setGenerationStep(0);
    }
  };

  const inputClass = "w-full px-4 py-3 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all bg-white";
  const labelClass = "block text-xs font-semibold text-slate-700 mb-1.5";

  return (
    <AppShell breadcrumbs={[{ label: "Clients", href: "/clients" }, { label: "New Estimate" }]}>
      <div className="max-w-7xl mx-auto">
        <div className="flex gap-6">
          {/* Main form area */}
          <div className="flex-1">
            {/* Stepper */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 mb-5">
              <div className="flex items-center justify-between">
                {STEPS.map((s, i) => (
                  <div key={s.id} className="flex items-center flex-1">
                    <button
                      onClick={() => s.id < step && setStep(s.id)}
                      className="flex flex-col items-center gap-1.5 group"
                    >
                      <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold transition-all ${
                        s.id < step
                          ? "bg-emerald-500 text-white"
                          : s.id === step
                          ? "text-white"
                          : "bg-slate-100 text-slate-400"
                      }`}
                        style={s.id === step ? { background: "linear-gradient(135deg, #2563eb, #7c3aed)" } : {}}>
                        {s.id < step ? <CheckCircle className="w-4 h-4" /> : <s.icon className="w-4 h-4" />}
                      </div>
                      <span className={`text-xs font-medium whitespace-nowrap ${s.id === step ? "text-blue-600" : s.id < step ? "text-emerald-600" : "text-slate-400"}`}>
                        {s.label}
                      </span>
                    </button>
                    {i < STEPS.length - 1 && (
                      <div className={`flex-1 h-0.5 mx-2 rounded transition-all ${s.id < step ? "bg-emerald-400" : "bg-slate-200"}`} />
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Step content */}
            <AnimatePresence mode="wait">
              <motion.div
                key={step}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
                className="bg-white rounded-2xl border border-slate-200 shadow-sm p-7"
              >
                {/* STEP 1 */}
                {step === 1 && (
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 mb-1">Customer & Deployment Mode</h2>
                    <p className="text-sm text-slate-500 mb-6">Basic information about the customer and deployment preference.</p>
                    <div className="space-y-5">
                      <div>
                        <label className={labelClass}>Customer Name</label>
                        <input className={inputClass} value={form.customerName} onChange={(e) => handleChange("customerName", e.target.value)} placeholder="e.g. ABC Bank" />
                      </div>
                      {/* Estimate Label */}
                      <div>
                        <label className={`${labelClass} flex items-center gap-1.5`}>
                          <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a2 2 0 012-2z" /></svg>
                          Estimate Label
                          <span className="ml-auto text-[10px] font-normal text-slate-400">optional</span>
                        </label>
                        <input
                          className={`${inputClass} text-sm`}
                          value={form.estimateLabel}
                          onChange={(e) => handleChange("estimateLabel", e.target.value)}
                          placeholder="e.g. Q3 2026 renewal, post-migration sizing, Phase 2 expansion…"
                          maxLength={120}
                        />
                        {form.estimateLabel && (
                          <p className="text-[10px] text-slate-400 mt-1">{form.estimateLabel.length}/120 characters</p>
                        )}
                      </div>
                      <div>
                        <label className={labelClass}>Deployment Mode</label>
                        <div className="grid grid-cols-2 gap-3">
                          {["SaaS", "On-Premise"].map((d) => (
                            <button key={d} onClick={() => handleChange("deployment", d)}
                              className={`py-4 px-5 rounded-xl border-2 text-sm font-semibold flex items-center gap-2 transition-all ${
                                form.deployment === d
                                  ? "border-blue-500 bg-blue-50 text-blue-700"
                                  : "border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                              }`}>
                              {d === "SaaS" ? <Cloud className="w-4 h-4" /> : <Server className="w-4 h-4" />}
                              <div className="text-left">
                                <p className="font-bold">{d}</p>
                                <p className="text-xs opacity-70">{d === "SaaS" ? "Cloud hosted by provider" : "Self-hosted infrastructure"}</p>
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Cloud Provider — only for SaaS */}
                      {form.deployment === "SaaS" && (
                        <div>
                          <label className={labelClass}>Cloud Provider(s)</label>
                          <p className="text-[11px] text-slate-400 mb-2">Select one or both. Separate sizing &amp; pricing reports will be generated per provider.</p>
                          <div className="flex gap-3">
                            {(["AWS", "GCP"] as const).map((p) => {
                              const checked = form.cloudProviders.includes(p);
                              const isAws = p === "AWS";
                              return (
                                <button key={p} type="button"
                                  onClick={() => {
                                    const next = checked
                                      ? form.cloudProviders.filter((x: string) => x !== p)
                                      : [...form.cloudProviders, p];
                                    if (next.length > 0) handleChange("cloudProviders", next);
                                  }}
                                  className={`flex items-center gap-3 px-5 py-3.5 rounded-xl border-2 text-sm font-semibold transition-all ${checked ? (isAws ? "border-amber-400 bg-amber-50 text-amber-700 ring-2 ring-amber-300" : "border-violet-400 bg-violet-50 text-violet-700 ring-2 ring-violet-300") : "border-slate-200 text-slate-500 hover:border-slate-300"}`}
                                >
                                  <span className={`w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold border-2 ${checked ? (isAws ? "bg-amber-100 border-amber-400 text-amber-700" : "bg-violet-100 border-violet-400 text-violet-700") : "border-slate-300 bg-white text-slate-400"}`}>{checked ? "✓" : ""}</span>
                                  <div className="text-left">
                                    <p className="font-bold">{p}</p>
                                    <p className="text-[10px] opacity-70">{isAws ? "Amazon Web Services" : "Google Cloud Platform"}</p>
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* STEP 2 */}
                {step === 2 && (
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 mb-1">Application Parameters</h2>
                    <p className="text-sm text-slate-500 mb-6">Define your application workload and usage requirements.</p>
                    <div className="space-y-4 mb-6">
                      {[
                        { key: "namedUsers", label: "Total Named Users (Y1)" },
                        { key: "concurrentUsers", label: "Concurrent Users (Y1)" },
                        { key: "concurrentMobileUsers", label: "Concurrent Mobile Users (Y1)" },
                        { key: "totalCustomers", label: "Total Customers (Y1)" },
                        { key: "numberOfLeads", label: "Number of Leads (Y1)" },
                        { key: "serviceRequests", label: "Number of Service Requests / Cases (Y1)" },
                      ].map((field) => (
                        <div key={field.key} className="flex gap-4 items-end">
                          <div className="flex-1">
                            <label className={labelClass}>{field.label}</label>
                            <input type="number" className={inputClass} value={(form as any)[field.key]} onChange={(e) => handleChange(field.key, parseInt(e.target.value))} />
                          </div>
                          <div className="w-32">
                            <label className={labelClass}>YoY %</label>
                            <div className="relative">
                              <select className={`${inputClass} appearance-none pr-8`} value={(form as any)[`${field.key}Yoy`]} onChange={(e) => handleChange(`${field.key}Yoy`, parseInt(e.target.value))}>
                                {[0, 5, 10, 15, 20, 25, 30].map(v => <option key={v} value={v}>{v}%</option>)}
                              </select>
                              <div className="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none text-slate-400">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div>
                      <label className={labelClass}>Modules Enabled</label>
                      <div className="grid grid-cols-3 gap-2">
                        {MODULES.map((m) => (
                          <label key={m} className="flex items-center gap-2 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50 transition-colors">
                            <input type="checkbox" checked={form.modules.includes(m)} onChange={() => toggleModule(m)}
                              className="w-4 h-4 rounded border-slate-300 text-blue-600" />
                            <span className="text-sm text-slate-700">{m}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div className="mt-8 border-t border-slate-200 pt-6">
                      <h3 className="text-md font-bold text-slate-900 mb-4 flex items-center gap-2">
                        <span className="text-blue-500">🔧</span> Detailed Sizing Assumptions
                      </h3>
                      <div className="grid grid-cols-4 gap-4 mb-4">
                        <div className="space-y-4">
                          <div>
                            <label className={labelClass}>Docs per customer</label>
                            <input type="number" className={inputClass} value={form.docsPerCustomer} onChange={(e) => handleChange("docsPerCustomer", parseInt(e.target.value) || 0)} />
                          </div>
                          <div>
                            <label className={labelClass}>Docs per Lead</label>
                            <input type="number" className={inputClass} value={form.docsPerLead} onChange={(e) => handleChange("docsPerLead", parseInt(e.target.value) || 0)} />
                          </div>
                          <div>
                            <label className={labelClass}>Docs per Case</label>
                            <input type="number" className={inputClass} value={form.docsPerCase} onChange={(e) => handleChange("docsPerCase", parseInt(e.target.value) || 0)} />
                          </div>
                        </div>
                        <div className="space-y-4">
                          <div>
                            <label className={labelClass}>Activities per customer</label>
                            <input type="number" className={inputClass} value={form.actsPerCustomer} onChange={(e) => handleChange("actsPerCustomer", parseInt(e.target.value) || 0)} />
                          </div>
                          <div>
                            <label className={labelClass}>Activities per Lead</label>
                            <input type="number" className={inputClass} value={form.actsPerLead} onChange={(e) => handleChange("actsPerLead", parseInt(e.target.value) || 0)} />
                          </div>
                          <div>
                            <label className={labelClass}>Activities per Case</label>
                            <input type="number" className={inputClass} value={form.actsPerCase} onChange={(e) => handleChange("actsPerCase", parseInt(e.target.value) || 0)} />
                          </div>
                        </div>
                        <div className="space-y-4">
                          <div>
                            <label className={labelClass}>PDF reports per user/hr</label>
                            <input type="number" className={inputClass} value={form.pdfPerUser} onChange={(e) => handleChange("pdfPerUser", parseInt(e.target.value) || 0)} />
                          </div>
                          <div>
                            <label className={labelClass}>Document size (MB)</label>
                            <input type="number" step="0.1" className={inputClass} value={form.docSizeMb} onChange={(e) => handleChange("docSizeMb", parseFloat(e.target.value) || 0)} />
                          </div>
                        </div>
                        <div className="space-y-4">
                          <div>
                            <label className={labelClass}>Emails ≈ {Math.floor((form.numberOfLeads + form.serviceRequests) * 0.05).toLocaleString()}</label>
                            <input type="number" className={`${inputClass} bg-slate-50 opacity-70`} disabled value={Math.floor((form.numberOfLeads + form.serviceRequests) * 0.05)} />
                          </div>
                          <div>
                            <label className={labelClass}>Escalations ≈ {Math.floor((form.totalCustomers + form.numberOfLeads + form.serviceRequests) * 0.10).toLocaleString()}</label>
                            <input type="number" className={`${inputClass} bg-slate-50 opacity-70`} disabled value={Math.floor((form.totalCustomers + form.numberOfLeads + form.serviceRequests) * 0.10)} />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* STEP 3 */}
                {step === 3 && (
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 mb-1">Database & Services</h2>
                    <p className="text-sm text-slate-500 mb-6">Select your primary database and advanced services.</p>
                    <div className="mb-6">
                      <label className={labelClass}>Primary Database</label>
                      <div className="grid grid-cols-3 gap-3">
                        {(form.deployment === "SaaS" ? ["PostgreSQL"] : ["PostgreSQL", "SQL Server", "Oracle"]).map((db) => (
                          <button key={db} onClick={() => handleChange("database", db)}
                            className={`py-3 px-4 rounded-xl border-2 text-sm font-semibold transition-all ${
                              form.database === db
                                ? "border-blue-500 bg-blue-50 text-blue-700"
                                : "border-slate-200 text-slate-600 hover:border-slate-300"
                            }`}>
                            {db}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className={labelClass}>Advanced Services</label>
                      <div className="space-y-3">
                        {[
                          { key: "clickhouse", label: "ClickHouse", desc: "OLAP analytics engine", dependsOn: "Analytics" },
                          { key: "aiServices", label: "AI Services", desc: "Predictive & GenAI workloads", dependsOn: "AI" },
                          { key: "redis", label: "Redis Cache", desc: "In-memory caching layer", dependsOn: null },
                        ].map((svc) => {
                          const isEnabled = !svc.dependsOn || form.modules.includes(svc.dependsOn);
                          const isChecked = isEnabled && (form as Record<string, unknown>)[svc.key];
                          
                          return (
                          <div key={svc.key}
                            className={`flex items-center justify-between p-4 rounded-xl border-2 transition-all ${
                              !isEnabled ? "opacity-60 bg-slate-50 border-slate-200 cursor-not-allowed" :
                              isChecked ? "border-blue-500 bg-blue-50 cursor-pointer" : "border-slate-200 hover:border-slate-300 cursor-pointer"
                            }`}
                            onClick={() => {
                              if (isEnabled) handleChange(svc.key, !isChecked);
                            }}>
                            <div>
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-semibold text-slate-800">{svc.label}</p>
                                {!isEnabled && <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 bg-slate-200 px-2 py-0.5 rounded-md">Requires {svc.dependsOn}</span>}
                              </div>
                              <p className="text-xs text-slate-500">{svc.desc}</p>
                            </div>
                            <div className={`w-11 h-6 rounded-full transition-all relative ${isChecked ? "bg-blue-500" : "bg-slate-300"}`}>
                              <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all ${isChecked ? "left-5" : "left-0.5"}`} />
                            </div>
                          </div>
                        )})}
                      </div>
                    </div>

                    {form.aiServices && form.modules.includes("AI") && (
                      <div className="mt-8 border-t border-slate-200 pt-6">
                        <h3 className="text-md font-bold text-slate-900 mb-4">AI Workload Configuration</h3>
                        
                        <div className="mb-4 p-4 rounded-xl border border-slate-200 bg-slate-50">
                          <div className="flex items-center gap-2 mb-3">
                            <input type="checkbox" checked={form.predictiveAi} onChange={(e) => handleChange("predictiveAi", e.target.checked)} className="w-4 h-4 text-blue-600 rounded border-slate-300 cursor-pointer" />
                            <span className="font-semibold text-slate-800 text-sm cursor-pointer" onClick={() => handleChange("predictiveAi", !form.predictiveAi)}>Predictive AI</span>
                          </div>
                          {form.predictiveAi && (
                            <div className="pl-6 border-l-2 border-slate-200 ml-2">
                              <label className={labelClass}>Target Environments</label>
                              <div className="flex flex-wrap gap-2">
                                {["prod", "training", "uat", "dr"].map(env => (
                                  <label key={env} className="flex items-center gap-2 text-xs bg-white border border-slate-200 px-3 py-1.5 rounded-lg cursor-pointer hover:border-blue-300 transition-colors">
                                    <input type="checkbox" checked={form.predictiveEnvs.includes(env)} onChange={(e) => {
                                      const newEnvs = e.target.checked ? [...form.predictiveEnvs, env] : form.predictiveEnvs.filter(x => x !== env);
                                      handleChange("predictiveEnvs", newEnvs);
                                    }} className="w-3.5 h-3.5 rounded text-blue-600" />
                                    {env.toUpperCase()}
                                  </label>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="mb-4 p-4 rounded-xl border border-slate-200 bg-slate-50">
                          <div className="flex items-center gap-2 mb-3">
                            <input type="checkbox" checked={form.genai} onChange={(e) => handleChange("genai", e.target.checked)} className="w-4 h-4 text-blue-600 rounded border-slate-300 cursor-pointer" />
                            <span className="font-semibold text-slate-800 text-sm cursor-pointer" onClick={() => handleChange("genai", !form.genai)}>GenAI Workloads</span>
                          </div>
                          {form.genai && (
                            <div className="pl-6 border-l-2 border-slate-200 ml-2 space-y-4">
                              <div>
                                <label className={labelClass}>Tokens per user per day</label>
                                <input type="number" className={inputClass} value={form.genaiTokens} onChange={(e) => handleChange("genaiTokens", parseInt(e.target.value) || 0)} />
                              </div>
                              <div>
                                <label className={labelClass}>Target Environments</label>
                                <div className="flex flex-wrap gap-2">
                                  {["prod", "uat", "dr"].map(env => (
                                    <label key={env} className="flex items-center gap-2 text-xs bg-white border border-slate-200 px-3 py-1.5 rounded-lg cursor-pointer hover:border-blue-300 transition-colors">
                                      <input type="checkbox" checked={form.genaiEnvs.includes(env)} onChange={(e) => {
                                        const newEnvs = e.target.checked ? [...form.genaiEnvs, env] : form.genaiEnvs.filter(x => x !== env);
                                        handleChange("genaiEnvs", newEnvs);
                                      }} className="w-3.5 h-3.5 rounded text-blue-600" />
                                      {env.toUpperCase()}
                                    </label>
                                  ))}
                                </div>
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
                          <div className="flex items-center gap-2 mb-3">
                            <input type="checkbox" checked={form.agenticAi} onChange={(e) => handleChange("agenticAi", e.target.checked)} className="w-4 h-4 text-blue-600 rounded border-slate-300 cursor-pointer" />
                            <span className="font-semibold text-slate-800 text-sm cursor-pointer" onClick={() => handleChange("agenticAi", !form.agenticAi)}>Agentic AI Workloads</span>
                          </div>
                          {form.agenticAi && (
                            <div className="pl-6 border-l-2 border-slate-200 ml-2 space-y-4">
                              <div>
                                <label className={labelClass}>Tasks per day</label>
                                <input type="number" className={inputClass} value={form.agenticTasks} onChange={(e) => handleChange("agenticTasks", parseInt(e.target.value) || 0)} />
                              </div>
                              <div>
                                <label className={labelClass}>Target Environments</label>
                                <div className="flex flex-wrap gap-2">
                                  {["prod", "uat", "dr"].map(env => (
                                    <label key={env} className="flex items-center gap-2 text-xs bg-white border border-slate-200 px-3 py-1.5 rounded-lg cursor-pointer hover:border-blue-300 transition-colors">
                                      <input type="checkbox" checked={form.agenticEnvs.includes(env)} onChange={(e) => {
                                        const newEnvs = e.target.checked ? [...form.agenticEnvs, env] : form.agenticEnvs.filter(x => x !== env);
                                        handleChange("agenticEnvs", newEnvs);
                                      }} className="w-3.5 h-3.5 rounded text-blue-600" />
                                      {env.toUpperCase()}
                                    </label>
                                  ))}
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                  </div>
                )}

                {/* STEP 4 */}
                {step === 4 && (
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 mb-1">Regions & Environments</h2>
                    <p className="text-sm text-slate-500 mb-6">Select deployment regions and additional environments.</p>
                    <div className="grid grid-cols-2 gap-5 mb-6">
                      <div>
                        <label className={labelClass}>AWS Region</label>
                        <select className={inputClass} value={form.awsRegion} onChange={(e) => handleChange("awsRegion", e.target.value)}>
                          {AWS_REGIONS.map((r) => <option key={r}>{r}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className={labelClass}>GCP Region</label>
                        <select className={inputClass} value={form.gcpRegion} onChange={(e) => handleChange("gcpRegion", e.target.value)}>
                          {GCP_REGIONS.map((r) => <option key={r}>{r}</option>)}
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className={labelClass}>Additional Environments</label>
                      <div className="grid grid-cols-3 gap-2">
                        {ENVIRONMENTS.map((env) => (
                          <label key={env} className="flex items-center gap-2 p-3 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50 transition-colors">
                            <input type="checkbox" checked={form.environments.includes(env)} onChange={() => toggleEnv(env)}
                              className="w-4 h-4 rounded border-slate-300 text-blue-600" />
                            <span className="text-sm font-medium text-slate-700">{env}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                    {form.environments.includes("DR") && (
                      <div className="mt-6 p-4 rounded-xl border border-slate-200 bg-slate-50">
                        <label className={labelClass}>DR Sizing Scale</label>
                        <p className="text-xs text-slate-500 mb-3">What percentage of production capacity should DR run at?</p>
                        <div className="flex gap-6">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input type="radio" name="drScale" checked={form.drScale === 50} onChange={() => handleChange("drScale", 50)} className="w-4 h-4 text-blue-600 border-slate-300 focus:ring-blue-500" />
                            <span className="text-sm font-semibold text-slate-700">50% of Production</span>
                          </label>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input type="radio" name="drScale" checked={form.drScale === 100} onChange={() => handleChange("drScale", 100)} className="w-4 h-4 text-blue-600 border-slate-300 focus:ring-blue-500" />
                            <span className="text-sm font-semibold text-slate-700">100% of Production</span>
                          </label>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* STEP 5 */}
                {step === 5 && (
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 mb-1">Financial Parameters</h2>
                    <p className="text-sm text-slate-500 mb-6">Configure discount, inflation, and contract duration.</p>
                    <div className="grid grid-cols-2 gap-5 mb-6">
                      <div>
                        <label className={labelClass}>Discount % ({form.discountPercent}%)</label>
                        <input type="range" min={0} max={40} value={form.discountPercent}
                          onChange={(e) => handleChange("discountPercent", parseInt(e.target.value))}
                          className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600" />
                        <div className="flex justify-between text-xs text-slate-400 mt-1"><span>0%</span><span>40%</span></div>
                      </div>
                      <div>
                        <label className={labelClass}>Inflation % ({form.inflationPercent}%)</label>
                        <input type="range" min={0} max={20} value={form.inflationPercent}
                          onChange={(e) => handleChange("inflationPercent", parseInt(e.target.value))}
                          className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600" />
                        <div className="flex justify-between text-xs text-slate-400 mt-1"><span>0%</span><span>20%</span></div>
                      </div>
                    </div>
                    <div>
                      <label className={labelClass}>Contract Duration</label>
                      <div className="grid grid-cols-3 gap-3">
                        {["1 Year", "3 Year", "5 Year"].map((d) => (
                          <button key={d} onClick={() => handleChange("contractDuration", d)}
                            className={`py-3 px-4 rounded-xl border-2 text-sm font-bold transition-all ${
                              form.contractDuration === d
                                ? "border-blue-500 bg-blue-50 text-blue-700"
                                : "border-slate-200 text-slate-600 hover:border-slate-300"
                            }`}>
                            {d}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="mt-8 border-t border-slate-200 pt-6">
                      <h3 className="text-md font-bold text-slate-900 mb-1 flex items-center gap-2">
                        <span className="text-amber-500">💰</span> One-Time Costs
                      </h3>
                      <p className="text-xs text-slate-500 mb-4">These are charged once in Year 1 and flow into the PUPM calculation.</p>
                      
                      <div className="grid grid-cols-3 gap-5 mb-4">
                        <div>
                          <label className={labelClass}>Performance Testing ($)</label>
                          <input type="number" className={inputClass} value={form.perfTestingCost} onChange={(e) => handleChange("perfTestingCost", parseInt(e.target.value) || 0)} />
                        </div>
                        <div>
                          <label className={labelClass}>Migration / Data Bootup ($)</label>
                          <input type="number" className={inputClass} value={form.migrationCost} onChange={(e) => handleChange("migrationCost", parseInt(e.target.value) || 0)} />
                        </div>
                        <div>
                          <label className={labelClass}>Managed Services Setup ($)</label>
                          <input type="number" className={inputClass} value={form.managedSvcCost} onChange={(e) => handleChange("managedSvcCost", parseInt(e.target.value) || 0)} />
                        </div>
                      </div>
                      
                      <div className="mt-4 p-4 rounded-xl border border-blue-100 bg-blue-50/50 flex items-center">
                        <span className="text-sm font-semibold text-slate-700 mr-2">Estimated One-Time Migration:</span>
                        <span className="text-lg font-bold text-blue-600">${(form.perfTestingCost + form.migrationCost + form.managedSvcCost).toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* STEP 6 — Review */}
                {step === 6 && !isGenerating && (
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 mb-1">Review Estimate</h2>
                    <p className="text-sm text-slate-500 mb-6">Review all parameters before generating the estimate.</p>
                    <div className="grid grid-cols-2 gap-4">
                      {[
                        { label: "Customer", value: form.customerName },
                        { label: "Deployment", value: form.deployment },
                        { label: "Named Users", value: form.namedUsers.toLocaleString() },
                        { label: "Concurrent Users", value: form.concurrentUsers.toLocaleString() },
                        { label: "Total Customers", value: form.totalCustomers.toLocaleString() },
                        { label: "Database", value: form.database },
                        { label: "AWS Region", value: form.awsRegion },
                        { label: "Environments", value: form.environments.join(", ") || "None" },
                        ...(form.environments.includes("DR") ? [{ label: "DR Scale", value: `${form.drScale}%` }] : []),
                        { label: "Discount", value: `${form.discountPercent}%` },
                        { label: "Inflation", value: `${form.inflationPercent}%` },
                        { label: "Contract", value: form.contractDuration },
                        { label: "Modules", value: form.modules.join(", ") },
                        { label: "Advanced Services", value: [form.clickhouse && "ClickHouse", form.aiServices && "AI Services", form.redis && "Redis"].filter(Boolean).join(", ") || "None" },
                      ].map((item) => (
                        <div key={item.label} className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                          <p className="text-xs font-semibold text-slate-500 mb-1">{item.label}</p>
                          <p className="text-sm font-bold text-slate-800">{item.value}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Generation Loading */}
                {isGenerating && (
                  <div className="flex flex-col items-center py-8">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                      className="w-16 h-16 border-4 border-blue-100 border-t-blue-600 rounded-full mb-6"
                    />
                    <h3 className="text-lg font-bold text-slate-900 mb-6">Generating Your Estimate...</h3>
                    <div className="w-full max-w-sm space-y-3">
                      {GENERATION_STEPS.map((gs, i) => (
                        <motion.div key={i}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: i <= generationStep ? 1 : 0.3, x: 0 }}
                          className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100">
                          {i < generationStep ? (
                            <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                          ) : i === generationStep ? (
                            <Loader2 className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" />
                          ) : (
                            <div className="w-4 h-4 rounded-full border-2 border-slate-300 flex-shrink-0" />
                          )}
                          <span className={`text-sm font-medium ${i <= generationStep ? "text-slate-800" : "text-slate-400"}`}>{gs}</span>
                        </motion.div>
                      ))}
                    </div>
                    <div className="w-full max-w-sm mt-6 bg-slate-200 rounded-full h-2">
                      <motion.div
                        className="h-full rounded-full"
                        style={{ background: "linear-gradient(90deg, #2563eb, #7c3aed)" }}
                        animate={{ width: `${((generationStep + 1) / GENERATION_STEPS.length) * 100}%` }}
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                  </div>
                )}

                {/* Nav buttons + error */}
                {!isGenerating && (
                  <>
                    <div className="flex items-center justify-between mt-8 pt-5 border-t border-slate-100">
                      <button onClick={() => setStep((s) => s - 1)} disabled={step === 1}
                        className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 disabled:opacity-40 transition-all">
                        <ChevronLeft className="w-4 h-4" /> Back
                      </button>
                      {step < 6 ? (
                        <motion.button onClick={() => setStep((s) => s + 1)}
                          whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
                          className="flex items-center gap-2 px-6 py-2.5 text-sm font-bold text-white rounded-xl btn-shine"
                          style={{ background: "linear-gradient(135deg, #2563eb, #1d4ed8)" }}>
                          Next <ChevronRight className="w-4 h-4" />
                        </motion.button>
                      ) : (
                        <motion.button onClick={handleGenerate}
                          disabled={isGenerating}
                          whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
                          className="flex items-center gap-2 px-6 py-2.5 text-sm font-bold text-white rounded-xl btn-shine"
                          style={{ background: "linear-gradient(135deg, #059669, #047857)" }}>
                          <Zap className="w-4 h-4" /> Generate Estimate
                        </motion.button>
                      )}
                    </div>
                    {/* API error banner */}
                    {generateError && (
                      <div className="mt-3 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700 flex items-start gap-2">
                        <span className="text-red-500 mt-0.5">⚠</span>
                        <div>
                          <p className="font-semibold">Generation failed</p>
                          <p className="text-xs mt-0.5 text-red-600">{generateError}</p>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Sticky summary panel */}
          <div className="w-72 flex-shrink-0">
            <div className="sticky top-20">
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-slate-900">Estimate Summary</h3>
                  <div className="flex items-center gap-1 text-xs text-emerald-600">
                    <Save className="w-3 h-3" />
                    <span>Auto-saved</span>
                  </div>
                </div>
                <div className="space-y-4">
                  {[
                    { label: "Users", value: form.concurrentUsers.toLocaleString(), icon: Users },
                    { label: "Deployment", value: form.deployment, icon: Cloud },
                    { label: "Environments", value: form.environments.length + 1, icon: Globe },
                    { label: "Database", value: form.database, icon: Database },
                    { label: "Modules", value: form.modules.length, icon: BarChart2 },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <item.icon className="w-3.5 h-3.5 text-slate-400" />
                        <span className="text-xs text-slate-500">{item.label}</span>
                      </div>
                      <span className="text-xs font-bold text-slate-800">{item.value}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-5 pt-4 border-t border-slate-100">
                  <p className="text-xs text-slate-500 mb-1">Estimated Monthly Cost</p>
                  <p className="text-2xl font-bold text-blue-600">{formatCurrency(estimatedCost)}</p>
                  <p className="text-xs text-slate-400 mt-1">AWS · {form.awsRegion.split(" ")[0]}</p>
                </div>
                <div className="mt-3 text-xs text-slate-400 flex items-center gap-1">
                  <Save className="w-3 h-3" />
                  Last saved: {autoSaved}
                </div>
              </div>

              {/* Step indicator */}
              <div className="mt-4 bg-white rounded-2xl border border-slate-200 shadow-sm p-4">
                <p className="text-xs font-semibold text-slate-500 mb-3">Progress</p>
                <div className="flex gap-1.5">
                  {STEPS.map((s) => (
                    <div key={s.id} className={`flex-1 h-1.5 rounded-full transition-all ${
                      s.id < step ? "bg-emerald-400" : s.id === step ? "bg-blue-500" : "bg-slate-200"
                    }`} />
                  ))}
                </div>
                <p className="text-xs text-slate-500 mt-2">Step {step} of {STEPS.length}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      <AICopilot />
    </AppShell>
  );
}

export default function EstimatorWizardPageWrapper() {
  return (
    <Suspense fallback={
      <AppShell breadcrumbs={[{ label: "Clients", href: "/clients" }, { label: "New Estimate" }]}>
        <div className="flex items-center justify-center py-32 text-slate-400">
          <Loader2 className="w-6 h-6 animate-spin mr-2" />
          <span className="text-sm">Loading...</span>
        </div>
      </AppShell>
    }>
      <EstimatorWizardPage />
    </Suspense>
  );
}
