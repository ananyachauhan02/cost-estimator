// ============================================================
// MOCK DATA — No backend connection
// ============================================================

export const MOCK_CLIENTS = [
  {
    id: "1",
    name: "ABC Bank",
    industry: "Banking & Finance",
    createdAt: "2026-06-15",
    estimateCount: 14,
    lastActivity: "2 hours ago",
    status: "active",
    logo: "AB",
    color: "from-blue-500 to-blue-700",
  },
  {
    id: "2",
    name: "XYZ Financial Services",
    industry: "Financial Services",
    createdAt: "2026-06-18",
    estimateCount: 8,
    lastActivity: "1 day ago",
    status: "active",
    logo: "XF",
    color: "from-violet-500 to-violet-700",
  },
  {
    id: "3",
    name: "Global Retail Ltd",
    industry: "Retail",
    createdAt: "2026-05-20",
    estimateCount: 11,
    lastActivity: "3 hours ago",
    status: "active",
    logo: "GR",
    color: "from-emerald-500 to-emerald-700",
  },
  {
    id: "4",
    name: "PQR Insurance",
    industry: "Insurance",
    createdAt: "2026-05-28",
    estimateCount: 5,
    lastActivity: "5 days ago",
    status: "active",
    logo: "PI",
    color: "from-orange-500 to-orange-700",
  },
  {
    id: "5",
    name: "LMN Technologies",
    industry: "Technology",
    createdAt: "2026-05-22",
    estimateCount: 3,
    lastActivity: "1 week ago",
    status: "active",
    logo: "LT",
    color: "from-pink-500 to-pink-700",
  },
  {
    id: "6",
    name: "OPQ Healthcare",
    industry: "Healthcare",
    createdAt: "2026-05-19",
    estimateCount: 6,
    lastActivity: "2 days ago",
    status: "active",
    logo: "OH",
    color: "from-teal-500 to-teal-700",
  },
];

export const MOCK_ESTIMATES = [
  {
    id: "v14",
    version: "V14",
    name: "Prod – Jun 2026",
    deployment: "SaaS",
    date: "15 Jun 2026",
    awsMonthlyCost: 12842,
    gcpMonthlyCost: 11250,
    status: "Completed",
  },
  {
    id: "v13",
    version: "V13",
    name: "Prod – May 2026",
    deployment: "SaaS",
    date: "10 May 2026",
    awsMonthlyCost: 11250,
    gcpMonthlyCost: 10100,
    status: "Completed",
  },
  {
    id: "v12",
    version: "V12",
    name: "DR – Apr 2026",
    deployment: "On-Premise",
    date: "16 Apr 2026",
    awsMonthlyCost: 8450,
    gcpMonthlyCost: 7800,
    status: "Completed",
  },
  {
    id: "v11",
    version: "V11",
    name: "Prod – Mar 2026",
    deployment: "SaaS",
    date: "10 Mar 2026",
    awsMonthlyCost: 8010,
    gcpMonthlyCost: 7300,
    status: "Completed",
  },
  {
    id: "v10",
    version: "V10",
    name: "Prod – Feb 2026",
    deployment: "SaaS",
    date: "02 Feb 2026",
    awsMonthlyCost: 8800,
    gcpMonthlyCost: 8100,
    status: "Completed",
  },
  {
    id: "v9",
    version: "V9",
    name: "UAT – Jan 2026",
    deployment: "SaaS",
    date: "15 Jan 2026",
    awsMonthlyCost: 6200,
    gcpMonthlyCost: 5800,
    status: "Completed",
  },
];

export const MOCK_RESULTS = {
  clientName: "ABC Bank",
  version: "V14",
  generatedAt: "19 Jun 2026 10:30 AM",
  deployment: "SaaS",
  awsMonthlyCost: 12842,
  awsAnnualCost: 154104,
  aws5YearTCO: 890321,
  gcpMonthlyCost: 11250,
  gcpAnnualCost: 135000,
  gcp5YearTCO: 783205,
  awsSavingsVsGcp: 107332,
  savingsPercent: 12,

  kpiCards: [
    { label: "Monthly Cost (AWS)", value: 12842, trend: "+6.2%", up: true },
    { label: "Annual Cost (AWS)", value: 154104, trend: "+8.1%", up: true },
    { label: "5 Year TCO (AWS)", value: 890321, trend: "+9.5%", up: true },
    { label: "AWS Savings vs GCP", value: 107332, trend: "12%", up: false },
  ],

  costTrend: [
    { year: "Year 1", aws: 154104, gcp: 135000 },
    { year: "Year 2", aws: 161809, gcp: 141750 },
    { year: "Year 3", aws: 169900, gcp: 148838 },
    { year: "Year 4", aws: 178395, gcp: 156280 },
    { year: "Year 5", aws: 226113, gcp: 163094 },
  ],

  environments: [
    { name: "Production", awsCost: 7842, gcpCost: 6900, resources: 24 },
    { name: "SIT", awsCost: 1800, gcpCost: 1600, resources: 8 },
    { name: "UAT", awsCost: 1600, gcpCost: 1400, resources: 6 },
    { name: "DR", awsCost: 1600, gcpCost: 1350, resources: 6 },
  ],

  infrastructure: {
    production: [
      { role: "Application Server (Master Node)", instance: "r6a.2xlarge", vcpu: 8, ram: 64, storage: "-", quantity: 4, cost: 1204.32 },
      { role: "Database Server (PostgreSQL)", instance: "r6a.4xlarge", vcpu: 16, ram: 128, storage: "1 TB GP3", quantity: 2, cost: 2500.60 },
      { role: "Cache (Redis)", instance: "r6a.large", vcpu: 2, ram: 16, storage: "-", quantity: 2, cost: 300.80 },
      { role: "Load Balancer", instance: "application-lb", vcpu: "-", ram: "-", storage: "-", quantity: 2, cost: 72.00 },
      { role: "Block Storage (EBS)", instance: "gp3", vcpu: "-", ram: "-", storage: "2 TB", quantity: 1, cost: 300.25 },
    ],
    sit: [
      { role: "Application Server", instance: "r6a.xlarge", vcpu: 4, ram: 32, storage: "-", quantity: 2, cost: 601.60 },
      { role: "Database Server", instance: "r6a.2xlarge", vcpu: 8, ram: 64, storage: "500 GB GP3", quantity: 1, cost: 800.30 },
    ],
    uat: [
      { role: "Application Server", instance: "r6a.xlarge", vcpu: 4, ram: 32, storage: "-", quantity: 2, cost: 601.60 },
      { role: "Database Server", instance: "r6a.2xlarge", vcpu: 8, ram: 64, storage: "500 GB GP3", quantity: 1, cost: 700.20 },
    ],
    dr: [
      { role: "Application Server", instance: "r6a.xlarge", vcpu: 4, ram: 32, storage: "-", quantity: 2, cost: 601.60 },
      { role: "Database Server (RDS Standby)", instance: "r6a.2xlarge", vcpu: 8, ram: 64, storage: "1 TB GP3", quantity: 1, cost: 900.40 },
    ],
  },

  aiRecommendations: [
    {
      type: "warning",
      title: "Memory-Optimized Instances (r6a)",
      desc: "Selected r6a instances save cost by 18% vs m6i for your memory-heavy workload.",
    },
    {
      type: "tip",
      title: "Reserved Instance (3 Year)",
      desc: "Switching to 3-Year Reserved would reduce cost by $1,870/month.",
    },
    {
      type: "info",
      title: "Consider removing DR environment",
      desc: "DR environment alone contributes $1,600/month. Evaluate if active-active is required.",
    },
  ],
};

export const AI_SUGGESTED_PROMPTS = [
  "How can I reduce monthly cloud costs?",
  "Compare AWS vs GCP for my workload",
  "What if concurrent users increase by 25%?",
  "How much does the DR environment cost?",
  "Explain the infrastructure sizing logic",
  "What is the 5-year TCO difference?",
];

export const AI_CHAT_HISTORY = [
  {
    id: "1",
    role: "assistant",
    content:
      "Hello! I'm your AI Cost Copilot. I have full context of your current estimate for **ABC Bank (V14)**. Ask me anything about cloud costs, sizing, or optimization.",
    timestamp: "10:30 AM",
  },
];

export const MOCK_STATS = {
  totalClients: 6,
  totalEstimates: 47,
  avgMonthlyCost: 11240,
  totalSavings: 312450,
};

export const SAVED_DRAFTS = [
  {
    id: "d1",
    name: "DEF Bank – Draft",
    client: "DEF Bank",
    step: 3,
    lastSaved: "2 hours ago",
    deployment: "SaaS",
    users: 8000,
  },
  {
    id: "d2",
    name: "GHI Corp – On-Prem",
    client: "GHI Corporation",
    step: 2,
    lastSaved: "1 day ago",
    deployment: "On-Premise",
    users: 15000,
  },
];

export const COMPARISON_SCENARIOS = [
  {
    id: "base",
    name: "Current Estimate",
    users: 5000,
    deployment: "SaaS",
    awsCost: 12842,
    gcpCost: 11250,
    description: "ABC Bank – V14",
  },
  {
    id: "a",
    name: "Scenario A",
    users: 7500,
    deployment: "SaaS",
    awsCost: 17200,
    gcpCost: 15100,
    description: "+25% users, same regions",
  },
  {
    id: "b",
    name: "Scenario B",
    users: 5000,
    deployment: "On-Premise",
    awsCost: 9800,
    gcpCost: 8600,
    description: "On-Prem migration estimate",
  },
];
