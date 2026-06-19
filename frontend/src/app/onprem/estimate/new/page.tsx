"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  User, Database, Globe, FileText, ChevronRight, ChevronLeft,
  Loader2, Cloud, Server, Box, Layers, CheckCircle,
} from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import { onpremApi, type OnpremCloud, type GenerateOnpremEstimateRequest } from "@/lib/api";

const STEPS = [
  { id: 1, label: "Customer", icon: User },
  { id: 2, label: "Cloud & Database", icon: Database },
  { id: 3, label: "Volumes & Environments", icon: Globe },
  { id: 4, label: "Review", icon: FileText },
];

const CLOUDS: { id: OnpremCloud; label: string; icon: typeof Cloud; blurb: string }[] = [
  { id: "aws",       label: "AWS",       icon: Cloud,  blurb: "Self-hosted on EC2 — AMD EPYC preferred, BYOL licensing" },
  { id: "gcp",       label: "GCP",       icon: Cloud,  blurb: "Managed equivalent (Cloud SQL) — AMD EPYC (N2D) preferred" },
  { id: "kubeadm",   label: "Kubeadm",   icon: Box,    blurb: "Self-hosted on customer VM/bare-metal cluster" },
  { id: "openshift", label: "OpenShift", icon: Layers, blurb: "Self-hosted on OpenShift-managed cluster" },
];

const DATABASES = ["PostgreSQL", "SQL Server", "Oracle"] as const;

const AWS_REGIONS = [
  "us-east-1 (N. Virginia)", "us-east-2 (Ohio)", "us-west-1 (N. California)",
  "us-west-2 (Oregon)", "ca-central-1 (Canada Central)", "sa-east-1 (São Paulo)",
  "eu-central-1 (Frankfurt)", "eu-west-1 (Ireland)", "eu-west-2 (London)",
  "eu-west-3 (Paris)", "eu-north-1 (Stockholm)",
  "ap-south-1 (Mumbai)", "ap-south-2 (Hyderabad)", "ap-northeast-1 (Tokyo)",
  "ap-northeast-2 (Seoul)", "ap-southeast-1 (Singapore)", "ap-southeast-2 (Sydney)",
  "me-south-1 (Bahrain)", "af-south-1 (Cape Town)",
];

const GCP_REGIONS = [
  "us-central1 (Iowa)", "us-east1 (South Carolina)", "us-west1 (Oregon)",
  "northamerica-northeast1 (Montréal)", "southamerica-east1 (São Paulo)",
  "europe-west1 (Belgium)", "europe-west3 (Frankfurt)", "europe-west2 (London)",
  "asia-south1 (Mumbai)", "asia-south2 (Delhi)", "asia-southeast1 (Singapore)",
  "asia-northeast1 (Tokyo)", "australia-southeast1 (Sydney)",
  "me-central1 (Doha)", "af-south1 (Johannesburg)",
];

const ENVIRONMENTS = ["Pre-Prod", "SIT", "UAT", "DR"];

function OnpremWizard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [step, setStep] = useState(1);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState(0);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const urlClientName = searchParams.get("clientName") ?? "";
  const clientId = searchParams.get("clientId") ?? undefined;

  const [form, setForm] = useState({
    customerName: urlClientName,
    estimateLabel: "",
    cloud: "aws" as OnpremCloud,
    database: "SQL Server" as "PostgreSQL" | "SQL Server" | "Oracle",
    region: "ap-south-1 (Mumbai)",
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
    environments: ["DR"] as string[],
    drScale: 100,
    contractDuration: "3 Year",
  });

  const handleChange = <K extends keyof typeof form>(key: K, value: typeof form[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const toggleEnv = (env: string) => {
    setForm((prev) => ({
      ...prev,
      environments: prev.environments.includes(env)
        ? prev.environments.filter((e) => e !== env)
        : [...prev.environments, env],
    }));
  };

  const showRegionPicker = form.cloud === "aws" || form.cloud === "gcp";
  const regionOptions = form.cloud === "aws" ? AWS_REGIONS : GCP_REGIONS;

  const GENERATION_STEPS = [
    "Recalculating Sizing Template…",
    "Distributing Worker Nodes…",
    `Sizing ${form.database} for ${CLOUDS.find((c) => c.id === form.cloud)?.label}…`,
    "Generating Sizing Workbook…",
    "Saving Estimate…",
  ];

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerateError(null);

    const stepInterval = setInterval(() => {
      setGenerationStep((prev) => (prev < GENERATION_STEPS.length - 1 ? prev + 1 : prev));
    }, 1500);

    try {
      const regionCode = form.region.split(" ")[0];

      const payload: GenerateOnpremEstimateRequest = {
        clientId: clientId ?? null,
        clientName: form.customerName || "Bank",
        database: form.database,
        cloud: form.cloud,
        region: showRegionPicker ? regionCode : null,

        namedUsers: form.namedUsers,
        concurrentUsers: form.concurrentUsers,
        concurrentMobileUsers: form.concurrentMobileUsers,
        totalCustomers: form.totalCustomers,
        numberOfLeads: form.numberOfLeads,
        serviceRequests: form.serviceRequests,

        namedUsersYoy: form.namedUsersYoy,
        concurrentUsersYoy: form.concurrentUsersYoy,
        concurrentMobileUsersYoy: form.concurrentMobileUsersYoy,
        totalCustomersYoy: form.totalCustomersYoy,
        numberOfLeadsYoy: form.numberOfLeadsYoy,
        serviceRequestsYoy: form.serviceRequestsYoy,

        environments: form.environments,
        drScale: form.drScale,
        contractDuration: form.contractDuration,
        estimateNotes: form.estimateLabel || "",
      };

      const result = await onpremApi.generate(payload);
      clearInterval(stepInterval);
      setGenerationStep(GENERATION_STEPS.length - 1);
      await new Promise((r) => setTimeout(r, 500));

      router.push(`/onprem/results?id=${result.estimateId}${clientId ? `&clientId=${clientId}` : ""}`);
    } catch (err: unknown) {
      clearInterval(stepInterval);
      setGenerateError(err instanceof Error ? err.message : String(err));
      setIsGenerating(false);
      setGenerationStep(0);
    }
  };

  const inputClass = "w-full px-4 py-3 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-400 transition-all bg-white";
  const labelClass = "block text-xs font-semibold text-slate-700 mb-1.5";

  return (
    <AppShell breadcrumbs={[{ label: "Clients", href: "/clients" }, { label: "On-Premise Sizing" }]}>
      <div className="max-w-4xl mx-auto">
        {/* On-Prem mode banner */}
        <div className="flex items-center gap-2 mb-5 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs font-semibold">
          <Server className="w-4 h-4" />
          On-Premise Sizing Module — infrastructure sizing only, no cost estimates are generated.
        </div>

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
                  }`} style={s.id === step ? { background: "linear-gradient(135deg, #d97706, #b45309)" } : {}}>
                    {s.id < step ? <CheckCircle className="w-4 h-4" /> : <s.icon className="w-4 h-4" />}
                  </div>
                  <span className={`text-[11px] font-semibold ${s.id === step ? "text-amber-700" : "text-slate-400"}`}>
                    {s.label}
                  </span>
                </button>
                {i < STEPS.length - 1 && (
                  <div className={`flex-1 h-0.5 mx-2 rounded-full ${s.id < step ? "bg-emerald-400" : "bg-slate-100"}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Form card */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-7">
          <AnimatePresence mode="wait">
            {step === 1 && (
              <motion.div key="s1" initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }}>
                <h2 className="text-lg font-bold text-slate-900 mb-1">Customer details</h2>
                <p className="text-sm text-slate-500 mb-6">Basic information for this on-premise sizing estimate.</p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={labelClass}>Customer / Bank Name</label>
                    <input className={inputClass} value={form.customerName}
                      onChange={(e) => handleChange("customerName", e.target.value)}
                      placeholder="e.g. HDFC Bank" />
                  </div>
                  <div>
                    <label className={labelClass}>Estimate Label (optional)</label>
                    <input className={inputClass} value={form.estimateLabel}
                      onChange={(e) => handleChange("estimateLabel", e.target.value)}
                      placeholder="e.g. Phase 1 — Core Banking" />
                  </div>
                </div>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div key="s2" initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }}>
                <h2 className="text-lg font-bold text-slate-900 mb-1">Cloud & database</h2>
                <p className="text-sm text-slate-500 mb-6">Choose the target infrastructure and database engine.</p>

                <label className={labelClass}>Cloud Platform</label>
                <div className="grid grid-cols-4 gap-3 mb-6">
                  {CLOUDS.map((c) => (
                    <button key={c.id} onClick={() => handleChange("cloud", c.id)}
                      className={`p-4 rounded-xl border-2 text-left transition-all ${
                        form.cloud === c.id ? "border-amber-500 bg-amber-50" : "border-slate-200 hover:border-slate-300"
                      }`}>
                      <c.icon className={`w-5 h-5 mb-2 ${form.cloud === c.id ? "text-amber-600" : "text-slate-400"}`} />
                      <p className="text-sm font-bold text-slate-900">{c.label}</p>
                      <p className="text-[11px] text-slate-500 mt-1 leading-snug">{c.blurb}</p>
                    </button>
                  ))}
                </div>

                <label className={labelClass}>Database Engine</label>
                <div className="grid grid-cols-3 gap-3 mb-6">
                  {DATABASES.map((db) => (
                    <button key={db} onClick={() => handleChange("database", db)}
                      className={`py-3 rounded-xl border-2 text-sm font-semibold transition-all ${
                        form.database === db ? "border-amber-500 bg-amber-50 text-amber-700" : "border-slate-200 text-slate-600 hover:border-slate-300"
                      }`}>
                      {db}
                    </button>
                  ))}
                </div>

                {showRegionPicker && (
                  <div>
                    <label className={labelClass}>{form.cloud === "aws" ? "AWS Region" : "GCP Region"}</label>
                    <select className={inputClass} value={form.region}
                      onChange={(e) => handleChange("region", e.target.value)}>
                      {regionOptions.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                    {form.database === "SQL Server" && form.cloud === "aws" && (
                      <p className="text-[11px] text-slate-500 mt-2">
                        SQL Server will be sized as self-hosted AMD EPYC compute (BYOL + AWS-owned Enterprise license) where available in this region, with an automatic equivalent fallback otherwise.
                      </p>
                    )}
                  </div>
                )}
                {!showRegionPicker && (
                  <p className="text-[11px] text-slate-500">
                    {CLOUDS.find((c) => c.id === form.cloud)?.label} sizing uses customer-provided hardware — no cloud region selection needed.
                  </p>
                )}
              </motion.div>
            )}

            {step === 3 && (
              <motion.div key="s3" initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }}>
                <h2 className="text-lg font-bold text-slate-900 mb-1">Volumes & environments</h2>
                <p className="text-sm text-slate-500 mb-6">Year-1 workload volumes and optional lower environments.</p>

                <div className="grid grid-cols-2 gap-4 mb-6">
                  {[
                    { key: "namedUsers" as const, label: "Named Users" },
                    { key: "concurrentUsers" as const, label: "Concurrent Users" },
                    { key: "concurrentMobileUsers" as const, label: "Concurrent Mobile Users" },
                    { key: "totalCustomers" as const, label: "Total Customers" },
                    { key: "numberOfLeads" as const, label: "Number of Leads" },
                    { key: "serviceRequests" as const, label: "Service Requests (Cases)" },
                  ].map((f) => (
                    <div key={f.key}>
                      <label className={labelClass}>{f.label}</label>
                      <input type="number" className={inputClass} value={form[f.key]}
                        onChange={(e) => handleChange(f.key, Number(e.target.value))} />
                    </div>
                  ))}
                </div>

                <label className={labelClass}>Lower Environments</label>
                <div className="grid grid-cols-4 gap-3 mb-6">
                  {ENVIRONMENTS.map((env) => (
                    <button key={env} onClick={() => toggleEnv(env)}
                      className={`py-2.5 rounded-xl border-2 text-sm font-semibold transition-all ${
                        form.environments.includes(env) ? "border-amber-500 bg-amber-50 text-amber-700" : "border-slate-200 text-slate-500 hover:border-slate-300"
                      }`}>
                      {env}
                    </button>
                  ))}
                </div>

                {form.environments.includes("DR") && (
                  <div className="mb-6">
                    <label className={labelClass}>DR Compute Scale</label>
                    <div className="flex gap-3">
                      {[50, 100].map((s) => (
                        <button key={s} onClick={() => handleChange("drScale", s)}
                          className={`flex-1 py-2.5 rounded-xl border-2 text-sm font-semibold transition-all ${
                            form.drScale === s ? "border-amber-500 bg-amber-50 text-amber-700" : "border-slate-200 text-slate-500 hover:border-slate-300"
                          }`}>
                          {s}% {s === 50 ? "(Pilot-light)" : "(Full Mirror)"}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <label className={labelClass}>Sizing Horizon</label>
                  <div className="flex gap-3">
                    {["1 Year", "3 Year", "5 Year"].map((y) => (
                      <button key={y} onClick={() => handleChange("contractDuration", y)}
                        className={`flex-1 py-2.5 rounded-xl border-2 text-sm font-semibold transition-all ${
                          form.contractDuration === y ? "border-amber-500 bg-amber-50 text-amber-700" : "border-slate-200 text-slate-500 hover:border-slate-300"
                        }`}>
                        {y}
                      </button>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {step === 4 && (
              <motion.div key="s4" initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }}>
                <h2 className="text-lg font-bold text-slate-900 mb-1">Review & generate</h2>
                <p className="text-sm text-slate-500 mb-6">Confirm the sizing inputs before generating the workbook.</p>

                <div className="grid grid-cols-2 gap-4 mb-6">
                  {[
                    { label: "Customer", value: form.customerName || "—" },
                    { label: "Cloud", value: CLOUDS.find((c) => c.id === form.cloud)?.label },
                    { label: "Database", value: form.database },
                    { label: "Region", value: showRegionPicker ? form.region : "On-Premise Data Center" },
                    { label: "Named Users", value: form.namedUsers.toLocaleString() },
                    { label: "Environments", value: form.environments.length ? form.environments.join(", ") : "Production only" },
                    { label: "Sizing Horizon", value: form.contractDuration },
                  ].map((item) => (
                    <div key={item.label} className="bg-slate-50 rounded-xl p-3.5">
                      <p className="text-[11px] text-slate-500 font-medium">{item.label}</p>
                      <p className="text-sm font-bold text-slate-900 mt-0.5">{item.value}</p>
                    </div>
                  ))}
                </div>

                {generateError && (
                  <div className="mb-4 p-3.5 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
                    {generateError}
                  </div>
                )}

                {isGenerating ? (
                  <div className="flex flex-col items-center gap-3 py-8">
                    <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
                    <p className="text-sm font-semibold text-slate-700">{GENERATION_STEPS[generationStep]}</p>
                  </div>
                ) : (
                  <button onClick={handleGenerate}
                    className="w-full py-3.5 rounded-xl text-white font-bold text-sm shadow-sm transition-all hover:shadow-md"
                    style={{ background: "linear-gradient(135deg, #d97706, #b45309)" }}>
                    Generate On-Premise Sizing
                  </button>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Nav buttons */}
        {!isGenerating && (
          <div className="flex justify-between mt-5">
            <button onClick={() => setStep((s) => Math.max(1, s - 1))} disabled={step === 1}
              className="flex items-center gap-1.5 px-5 py-2.5 text-sm font-semibold text-slate-600 disabled:opacity-0 transition-opacity">
              <ChevronLeft className="w-4 h-4" /> Back
            </button>
            {step < STEPS.length && (
              <button onClick={() => setStep((s) => Math.min(STEPS.length, s + 1))}
                className="flex items-center gap-1.5 px-5 py-2.5 text-sm font-bold text-white rounded-xl"
                style={{ background: "linear-gradient(135deg, #d97706, #b45309)" }}>
                Continue <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default function OnpremWizardPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-slate-400">Loading…</div>}>
      <OnpremWizard />
    </Suspense>
  );
}
