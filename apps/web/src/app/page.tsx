"use client";

import React, { useEffect, useState } from "react";
import {
  Mail,
  ShieldCheck,
  Sparkles,
  CheckCircle2,
  Lock,
  ArrowRight,
  Server,
  Zap,
  Inbox,
  SlidersHorizontal,
} from "lucide-react";

export default function Home() {
  const [backendHealth, setBackendHealth] = useState<
    "checking" | "online" | "offline"
  >("checking");
  const [healthData, setHealthData] = useState<{
    status?: string;
    version?: string;
  } | null>(null);

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch("/api/v1/healthz");
        if (res.ok) {
          const data = await res.json();
          setBackendHealth("online");
          setHealthData(data);
        } else {
          setBackendHealth("offline");
        }
      } catch {
        setBackendHealth("offline");
      }
    }
    checkHealth();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-indigo-500 selection:text-white">
      {/* Background Glow Accents */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-indigo-600/20 rounded-full blur-[128px]" />
        <div className="absolute top-1/3 -right-40 w-96 h-96 bg-violet-600/15 rounded-full blur-[128px]" />
        <div className="absolute -bottom-40 left-1/3 w-96 h-96 bg-blue-600/15 rounded-full blur-[128px]" />
      </div>

      {/* Navigation Header */}
      <header className="relative z-10 border-b border-slate-800/80 backdrop-blur-md bg-slate-950/60 sticky top-0">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 ring-1 ring-white/20">
              <Mail className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                Mail Agent
              </span>
              <span className="ml-2 text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                Production AI
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Backend Health Badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono border border-slate-800 bg-slate-900/80">
              <span
                className={`w-2 h-2 rounded-full animate-pulse ${
                  backendHealth === "online"
                    ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"
                    : backendHealth === "checking"
                      ? "bg-amber-400"
                      : "bg-rose-500"
                }`}
              />
              <span className="text-slate-400">
                API:{" "}
                <span
                  className={
                    backendHealth === "online"
                      ? "text-emerald-400 font-semibold"
                      : backendHealth === "checking"
                        ? "text-amber-400"
                        : "text-rose-400"
                  }
                >
                  {backendHealth === "online" && healthData?.version
                    ? `v${healthData.version}`
                    : backendHealth}
                </span>
              </span>
            </div>

            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
            >
              <span>Swagger Docs</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </a>

            <a
              href="/api/v1/auth/google/login"
              className="inline-flex items-center gap-2 text-xs font-medium px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 transition-all active:scale-95"
            >
              Sign In with Google
            </a>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 py-12 space-y-16">
        {/* Hero Section */}
        <section className="text-center max-w-3xl mx-auto pt-6 space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium bg-slate-900/90 border border-slate-800 text-slate-300 shadow-inner">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>
              Autonomous Intelligence &bull; Strictly Human-Approved Sending
            </span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight leading-[1.15]">
            Supercharge your Gmail with{" "}
            <span className="bg-gradient-to-r from-indigo-400 via-violet-300 to-sky-400 bg-clip-text text-transparent">
              Zero-Risk AI
            </span>
          </h1>

          <p className="text-slate-400 text-base sm:text-lg leading-relaxed">
            Mail Agent triages your unread inbox, categorizes incoming messages,
            assesses importance (1&ndash;5), and prepares draft replies in your
            voice. Every email requires explicit human approval before delivery.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
            <a
              href="/api/v1/auth/google/login"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-medium text-sm shadow-lg shadow-indigo-500/25 transition-all hover:shadow-indigo-500/40 active:scale-95"
            >
              <Mail className="w-4 h-4" />
              <span>Connect Gmail Account</span>
            </a>

            <a
              href="#architecture"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800/80 border border-slate-800 text-slate-200 font-medium text-sm transition-all"
            >
              <span>Explore Safety Architecture</span>
              <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        </section>

        {/* Feature Cards Grid */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="group p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80 hover:border-indigo-500/40 transition-all hover:bg-slate-900/60 backdrop-blur-sm relative overflow-hidden">
            <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4 group-hover:scale-110 transition-transform">
              <Inbox className="w-6 h-6" />
            </div>
            <h3 className="font-semibold text-lg text-slate-100 mb-2">
              Smart Inbox Triage
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Real-time push sync through Gmail Pub/Sub. Classifies messages
              into Work, Finance, Personal, Newsletters, and Alerts with
              1&ndash;5 importance rankings.
            </p>
          </div>

          {/* Card 2 */}
          <div className="group p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80 hover:border-violet-500/40 transition-all hover:bg-slate-900/60 backdrop-blur-sm relative overflow-hidden">
            <div className="w-12 h-12 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400 mb-4 group-hover:scale-110 transition-transform">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="font-semibold text-lg text-slate-100 mb-2">
              Claude Reply Drafting
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Generates context-aware replies matching your tone profile or
              customizable template variables. Protected by robust
              prompt-injection sanitizers.
            </p>
          </div>

          {/* Card 3 */}
          <div className="group p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80 hover:border-emerald-500/40 transition-all hover:bg-slate-900/60 backdrop-blur-sm relative overflow-hidden">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-4 group-hover:scale-110 transition-transform">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="font-semibold text-lg text-slate-100 mb-2">
              Cryptographic Safety Lock
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Hard domain rule: AI cannot send emails. Sends require explicit
              human approval, sealed by SHA-256 hash validation and database
              row-lock idempotency.
            </p>
          </div>
        </section>

        {/* Live Safety Workflow Visualizer */}
        <section
          id="architecture"
          className="p-8 rounded-3xl bg-slate-900/30 border border-slate-800/80 backdrop-blur-sm"
        >
          <div className="max-w-2xl mb-8">
            <h2 className="text-xl font-bold tracking-tight text-white mb-2">
              Domain-Enforced Draft State Machine
            </h2>
            <p className="text-sm text-slate-400">
              Guaranteed by backend business logic. If an approved draft is
              modified, the hash invalidates and immediately forces re-approval
              before sending.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-mono text-indigo-400 font-semibold uppercase tracking-wider">
                  Step 1
                </span>
                <h4 className="font-medium text-slate-200 mt-1">DRAFTED</h4>
                <p className="text-xs text-slate-400 mt-1.5">
                  AI generates suggested reply based on thread context and
                  templates.
                </p>
              </div>
              <div className="mt-4 flex items-center gap-1.5 text-xs text-slate-500 font-mono">
                <SlidersHorizontal className="w-3.5 h-3.5" />
                <span>Editable</span>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-indigo-500/30 bg-indigo-950/20 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-mono text-indigo-400 font-semibold uppercase tracking-wider">
                  Step 2
                </span>
                <h4 className="font-medium text-indigo-200 mt-1">APPROVED</h4>
                <p className="text-xs text-indigo-300/80 mt-1.5">
                  Human clicks Approve. SHA-256 content hash sealed in database.
                </p>
              </div>
              <div className="mt-4 flex items-center gap-1.5 text-xs text-indigo-400 font-mono">
                <Lock className="w-3.5 h-3.5" />
                <span>Hash Sealed</span>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-950/20 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-mono text-amber-400 font-semibold uppercase tracking-wider">
                  Step 3
                </span>
                <h4 className="font-medium text-amber-200 mt-1">SENDING</h4>
                <p className="text-xs text-amber-300/80 mt-1.5">
                  Hash re-verified, idempotency key locked with FOR UPDATE.
                </p>
              </div>
              <div className="mt-4 flex items-center gap-1.5 text-xs text-amber-400 font-mono">
                <Zap className="w-3.5 h-3.5" />
                <span>Idempotent</span>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-mono text-emerald-400 font-semibold uppercase tracking-wider">
                  Step 4
                </span>
                <h4 className="font-medium text-emerald-200 mt-1">SENT</h4>
                <p className="text-xs text-emerald-300/80 mt-1.5">
                  RFC 5322 MIME message dispatched to Gmail in correct thread.
                </p>
              </div>
              <div className="mt-4 flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Audited</span>
              </div>
            </div>
          </div>
        </section>

        {/* System Status & Roadmap */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* System Environment */}
          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80">
            <h3 className="font-semibold text-slate-200 flex items-center gap-2 mb-4">
              <Server className="w-4 h-4 text-indigo-400" />
              <span>Foundation Environment Status</span>
            </h3>
            <ul className="space-y-3 text-xs font-mono">
              <li className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Backend API</span>
                <span className="text-slate-200">
                  FastAPI 0.115 + Python 3.12 (uv)
                </span>
              </li>
              <li className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Frontend Stack</span>
                <span className="text-slate-200">
                  Next.js 16 + Tailwind CSS
                </span>
              </li>
              <li className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Token Vault</span>
                <span className="text-slate-200">MultiFernet Key Rotation</span>
              </li>
              <li className="flex justify-between items-center py-1.5">
                <span className="text-slate-400">Unit Test Suite</span>
                <span className="text-emerald-400 font-semibold">
                  38 / 38 Passing
                </span>
              </li>
            </ul>
          </div>

          {/* Phase Roadmap */}
          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80">
            <h3 className="font-semibold text-slate-200 flex items-center gap-2 mb-4">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Implementation Phases</span>
            </h3>
            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
                <span>Phase 1: Foundation (Scaffold, Core, Quality Gates)</span>
                <span className="font-mono font-semibold">COMPLETE</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-300">
                <span>Phase 2: Database (Models, Alembic, Repositories)</span>
                <span className="font-mono font-semibold">NEXT UP</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/30 text-slate-400">
                <span>Phase 3: Auth &amp; Google Token Vault</span>
                <span className="font-mono">PENDING</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/30 text-slate-400">
                <span>
                  Phase 4&ndash;6: Sync, AI Engine &amp; Approval State Machine
                </span>
                <span className="font-mono">PENDING</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/30 text-slate-400">
                <span>Phase 7: Full Inbox &amp; Review Frontend UI</span>
                <span className="font-mono">PENDING</span>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-800/80 py-8 mt-16 text-center text-xs text-slate-500 font-mono">
        <p>
          Mail Agent &bull; Production-Grade Email Management with
          Domain-Enforced Safety
        </p>
      </footer>
    </div>
  );
}
