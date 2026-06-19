/**
 * api.ts — Typed API client for BusinessNext Cost Estimator.
 * All fetch() calls go through here. Automatically attaches JWT token.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "businessnext_token";

// ── Token helpers ────────────────────────────────────────────────────────────

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// ── Base fetch ───────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    window.location.href = "/";
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API error");
  }

  // No content (204 / DELETE responses)
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return {} as T;
  }

  return res.json();
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  status: string;
  lastLogin: string;
  created_at?: string;
}

export interface Client {
  id: string;
  name: string;
  industry: string;
  createdAt: string;
  estimateCount: number;
  lastActivity: string;
  status: string;
  logo: string;
  color: string;
}

export interface Estimate {
  id: string;
  version: string;
  name: string;
  deployment: string;
  date: string;
  awsMonthlyCost: number;
  gcpMonthlyCost: number;
  status: string;
  dbType: string;
  years: number;
  notes: string;
}

export interface EstimateDetail {
  id: string;
  clientId: string;
  customerName: string;
  version: string;
  clientMode: string;
  cloudProviders?: string[];   // ["AWS"], ["GCP"], or ["AWS","GCP"]
  dbType: string;
  generatedAt: string;
  awsMonthlyCost: number;
  awsAnnualCost: number;
  aws5YearTCO: number;
  gcpMonthlyCost: number;
  awsSavingsVsGcp: number;
  savingsPercent: number;
  gcpRegion: string;
  gcpPricedRoles: {
    role_key: string; label: string; category?: string;
    nodes: number; vcpu_per_node?: number | string; ram_per_node?: number | string;
    storage_per_node_gb?: number; instance_type?: string; gcp_instance_type?: string;
    monthly_usd: number; gcp_note?: string;
  }[];
  gcpComparison: {
    summary?: {
      aws_monthly: number; gcp_monthly: number;
      aws_annual: number; gcp_annual: number;
      aws_5year: number; gcp_5year: number;
      cheaper_monthly: string; cheaper_annual: string; cheaper_5year: string;
      diff_monthly: number; diff_annual: number; diff_5year: number;
      aws_vs_gcp_monthly_pct: number;
      aws_region: string; gcp_region: string;
    };
    category_comparison?: {
      category: string; aws_monthly: number; gcp_monthly: number;
      diff: number; cheaper: string; pct_diff: number;
    }[];
  };
  costTrend: { year: string; aws: number; gcp: number }[];
  distribution: Record<string, unknown>;
  pricedRoles: {
    role_key: string; label: string; category: string;
    nodes: number; vcpu_per_node: number | string; ram_per_node: number | string;
    storage_per_node_gb?: number; instance_type?: string;
    monthly_usd: number;
  }[];
  environments: Record<string, unknown>;
  metrics: Record<string, unknown>;
}

export interface AuthResponse {
  token: string;
  user: { id: number; email: string; name: string; role: string };
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    apiFetch<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => apiFetch<User>("/api/auth/me"),
};

// ── Users ─────────────────────────────────────────────────────────────────────

export const usersApi = {
  list: () => apiFetch<User[]>("/api/users"),

  create: (data: { email: string; password: string; name?: string; role: string }) =>
    apiFetch<{ id: number; message: string }>("/api/users", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: { role: string; name?: string }) =>
    apiFetch<{ message: string }>(`/api/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    apiFetch<{ message: string }>(`/api/users/${id}`, { method: "DELETE" }),

  resetPassword: (id: string, newPassword: string) =>
    apiFetch<{ message: string }>(`/api/users/${id}/reset-password`, {
      method: "POST",
      body: JSON.stringify({ new_password: newPassword }),
    }),
};

// ── Clients ───────────────────────────────────────────────────────────────────

export const clientsApi = {
  list: () => apiFetch<Client[]>("/api/clients"),

  create: (name: string, sector: string) =>
    apiFetch<Client>("/api/clients", {
      method: "POST",
      body: JSON.stringify({ name, sector }),
    }),

  get: (id: string) => apiFetch<Client>(`/api/clients/${id}`),

  delete: (id: string) =>
    apiFetch<{ message: string }>(`/api/clients/${id}`, { method: "DELETE" }),
};

// ── Estimates ─────────────────────────────────────────────────────────────────

export const estimatesApi = {
  listByClient: (clientId: string) =>
    apiFetch<Estimate[]>(`/api/clients/${clientId}/estimates`),

  get: (id: string) => apiFetch<EstimateDetail>(`/api/estimates/${id}`),

  delete: (id: string) =>
    apiFetch<{ message: string }>(`/api/estimates/${id}`, { method: "DELETE" }),

  // Excel file downloads (sizing / pricing)
  downloadUrl: (id: string, type: "sizing" | "pricing") =>
    `${API_URL}/api/estimates/${id}/files/${type}`,

  // PDF report download
  pdfUrl: (id: string) =>
    `${API_URL}/api/estimates/${id}/files/pdf`,

  // Full ZIP bundle download
  downloadAllUrl: (id: string) =>
    `${API_URL}/api/estimates/${id}/download-all`,
};

// ── On-Premise Sizing (separate from SaaS — sizing only, no pricing) ──────────

export type OnpremCloud = "aws" | "gcp" | "kubeadm" | "openshift";

export interface OnpremDbSizing {
  cloud: string;
  db_type: string;
  hosting_model: string;
  licensing: string;
  category: string;
  primary_label: string;
  cluster_info: string;
  os: string;
  region: string;
  primary_nodes: number;
  vcpu_per_node: number;
  ram_per_node_gb: number;
  instance_type: string;
  instance_family?: string;
  managed_tier_label?: string;
  amd_preferred: boolean | null;
  amd_available_in_region: boolean | null;
  amd_selected: boolean | null;
  selection_note: string;
  total_db_ram_gb_requested: number;
}

export interface OnpremStorageSizing {
  primary_san_gb: number;
  reporting_san_gb: number;
  object_storage_gb: number;
  label_primary: string;
  label_reporting: string;
  label_object: string;
}

export interface GenerateOnpremEstimateRequest {
  clientId?: string | null;
  clientName: string;
  database: "PostgreSQL" | "SQL Server" | "Oracle";
  cloud: OnpremCloud;
  region?: string | null;

  namedUsers: number;
  concurrentUsers: number;
  concurrentMobileUsers: number;
  totalCustomers: number;
  numberOfLeads: number;
  serviceRequests: number;

  namedUsersYoy: number;
  concurrentUsersYoy: number;
  concurrentMobileUsersYoy: number;
  totalCustomersYoy: number;
  numberOfLeadsYoy: number;
  serviceRequestsYoy: number;

  environments: string[];
  drScale: number;
  contractDuration: string;

  estimateNotes?: string;
}

export interface OnpremEstimateResult {
  success: boolean;
  estimateId: string;
  customerName: string;
  clientMode: "onprem";
  cloud: OnpremCloud;
  database: string;
  dbSizing: { cloud: string; db_type: string; db: OnpremDbSizing; storage: OnpremStorageSizing };
  metrics: {
    workerNodes: number;
    totalVcpus: number;
    totalRamGb: number;
    dataSizeGb: number;
    s3SizeGb: number;
  };
  distribution: Record<string, unknown>;
  excelGenerated: boolean;
}

export const onpremApi = {
  generate: (body: GenerateOnpremEstimateRequest) =>
    apiFetch<OnpremEstimateResult>("/api/generate-onprem-estimate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

// ── Health ────────────────────────────────────────────────────────────────────

export const healthApi = {
  check: () => apiFetch<{ status: string }>("/api/health"),
};
