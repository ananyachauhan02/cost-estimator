import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "BusinessNext | Intelligent Cloud Cost Estimator",
  description:
    "From Requirements to Real-Time Cloud Cost Insights in Minutes. Enterprise SaaS platform for cloud cost estimation.",
  keywords: ["cloud cost", "AWS", "GCP", "cost estimator", "BusinessNext"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased bg-slate-50 text-slate-900">{children}</body>
    </html>
  );
}
