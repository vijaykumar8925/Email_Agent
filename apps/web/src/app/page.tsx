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
  Cpu,
  RefreshCw,
  Send,
  AlertTriangle,
  Bot,
  Layers,
  LayoutDashboard,
} from "lucide-react";
import { InboxView } from "@/features/inbox";
import { ThemeToggle } from "@/components";

interface AIHealthData {
  provider: string;
  status: string;
  base_url: string;
  classifier_model: string;
  drafter_model: string;
  available_models: string[];
}

interface TriageResult {
  category: string;
  importance: number;
  needs_reply: boolean;
  summary: string;
  suggested_action: string;
  reasoning_short: string;
  model_used: string;
  latency_ms: number;
}

interface DraftResult {
  subject: string;
  body: string;
  tone: string;
  model_used: string;
  latency_ms: number;
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<"inbox" | "playground" | "architecture">("inbox");
  const [backendHealth, setBackendHealth] = useState<
    "checking" | "online" | "offline"
  >("checking");
  const [healthData, setHealthData] = useState<{
    status?: string;
    version?: string;
  } | null>(null);
  const [currentUser, setCurrentUser] = useState<{
    id: string;
    email: string;
    name: string;
    display_name?: string;
    picture_url?: string;
  } | null>(null);

  // AI Subsystem State
  const [aiHealth, setAiHealth] = useState<AIHealthData | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  // Playground State
  const [testSubject, setTestSubject] = useState(
    "Urgent: Budget approval needed for cloud migration"
  );
  const [testSender, setTestSender] = useState("alex.finance@acme.corp");
  const [testBody, setTestBody] = useState(
    "Hi Vijay,\n\nWe have received the revised proposal for Q4 cloud migration. The total cost is $14,500. Could you please confirm if this fits within your department's allocation so we can proceed with procurement today?\n\nThanks,\nAlex"
  );
  const [triageResult, setTriageResult] = useState<TriageResult | null>(null);
  const [draftResult, setDraftResult] = useState<DraftResult | null>(null);
  const [playgroundError, setPlaygroundError] = useState<string | null>(null);

  const fetchAIHealth = async () => {
    try {
      const res = await fetch("/api/v1/ai/status");
      if (res.ok) {
        const data = await res.json();
        setAiHealth(data);
      }
    } catch {
      // AI status call error
    }
  };

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

    async function checkAuth() {
      try {
        const res = await fetch("/api/v1/auth/status");
        if (res.ok) {
          const data = await res.json();
          if (data.authenticated && data.user) {
            setCurrentUser(data.user);
          }
        }
      } catch {
        // Not authenticated
      }
    }

    checkHealth();
    checkAuth();
    fetchAIHealth();
  }, []);

  const handleLogout = async () => {
    try {
      await fetch("/api/v1/auth/logout", { method: "POST" });
      setCurrentUser(null);
    } catch {
      // ignore
    }
  };

  const handleRunTriage = async () => {
    setAiLoading(true);
    setPlaygroundError(null);
    setTriageResult(null);
    try {
      const res = await fetch("/api/v1/ai/triage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject: testSubject,
          sender: testSender,
          body: testBody,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Triage failed");
      }
      const data = await res.json();
      setTriageResult(data);
    } catch (e: unknown) {
      setPlaygroundError(e instanceof Error ? e.message : "Error analyzing email");
    } finally {
      setAiLoading(false);
    }
  };

  const handleGenerateDraft = async () => {
    setAiLoading(true);
    setPlaygroundError(null);
    setDraftResult(null);
    try {
      const res = await fetch("/api/v1/ai/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email_subject: testSubject,
          email_sender: testSender,
          email_body: testBody,
          user_instructions: "Approve the budget allocation and request the purchase order invoice.",
          tone: "professional",
          sender_name: currentUser?.display_name || "Vijay",
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Drafting failed");
      }
      const data = await res.json();
      setDraftResult(data);
    } catch (e: unknown) {
      setPlaygroundError(e instanceof Error ? e.message : "Error generating draft");
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100 selection:bg-indigo-500 selection:text-white flex flex-col justify-between transition-colors duration-200">
      {/* Background Glow Accents */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-indigo-500/10 dark:bg-indigo-600/20 rounded-full blur-[128px]" />
        <div className="absolute top-1/3 -right-40 w-96 h-96 bg-violet-500/10 dark:bg-violet-600/15 rounded-full blur-[128px]" />
        <div className="absolute -bottom-40 left-1/3 w-96 h-96 bg-emerald-500/5 dark:bg-emerald-600/10 rounded-full blur-[128px]" />
      </div>

      {/* Navigation Header */}
      <header className="relative z-10 border-b border-slate-200/80 dark:border-slate-800/80 backdrop-blur-md bg-white/75 dark:bg-slate-950/70 sticky top-0 transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 ring-1 ring-white/20">
              <Mail className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-700 dark:from-white dark:via-slate-100 dark:to-slate-400 bg-clip-text text-transparent">
                Mail Agent
              </span>
              <span className="ml-2 text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
                Ollama Local AI
              </span>
            </div>
          </div>

          {/* Central Tab Navigation */}
          <nav className="hidden md:flex items-center gap-1.5 p-1 rounded-2xl bg-slate-200/70 border border-slate-300/60 dark:bg-slate-900/80 dark:border-slate-800 transition-colors">
            <button
              onClick={() => setActiveTab("inbox")}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer ${
                activeTab === "inbox"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/25"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              }`}
            >
              <Inbox className="w-3.5 h-3.5" />
              <span>Smart Inbox</span>
            </button>

            <button
              onClick={() => setActiveTab("playground")}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer ${
                activeTab === "playground"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/25"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>AI Playground</span>
            </button>

            <button
              onClick={() => setActiveTab("architecture")}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer ${
                activeTab === "architecture"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/25"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Safety &amp; Roadmap</span>
            </button>
          </nav>

          <div className="flex items-center gap-3">
            {/* AI Status Badge */}
            <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 shadow-xs">
              <Cpu className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" />
              <span className="text-slate-600 dark:text-slate-400">
                Model:{" "}
                <span className="text-indigo-600 dark:text-indigo-300 font-semibold">
                  {aiHealth?.classifier_model || "phi4-mini:latest"}
                </span>
              </span>
            </div>

            {/* Backend Health Badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 shadow-xs">
              <span
                className={`w-2 h-2 rounded-full animate-pulse ${
                  backendHealth === "online"
                    ? "bg-emerald-500 shadow-[0_0_8px_rgba(52,211,153,0.8)]"
                    : backendHealth === "checking"
                      ? "bg-amber-500"
                      : "bg-rose-500"
                }`}
              />
              <span className="text-slate-600 dark:text-slate-400">
                API:{" "}
                <span
                  className={
                    backendHealth === "online"
                      ? "text-emerald-600 dark:text-emerald-400 font-semibold"
                      : backendHealth === "checking"
                        ? "text-amber-600 dark:text-amber-400"
                        : "text-rose-600 dark:text-rose-400"
                  }
                >
                  {backendHealth === "online" && healthData?.version
                    ? `v${healthData.version}`
                    : backendHealth}
                </span>
              </span>
            </div>

            {/* Theme Toggle Component */}
            <ThemeToggle />

            {/* User Profile / Disconnect */}
            {currentUser ? (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleLogout}
                  title={`Disconnect ${currentUser.email}`}
                  className="px-2.5 py-1 rounded-xl text-xs font-mono text-slate-600 hover:text-rose-600 hover:bg-rose-50 dark:text-slate-400 dark:hover:text-rose-400 dark:hover:bg-rose-500/10 transition-colors cursor-pointer border border-slate-200 dark:border-slate-800 shadow-xs"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <a
                href="/api/v1/auth/google/login"
                className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 text-white text-xs font-semibold shadow-md shadow-indigo-500/20 hover:from-indigo-600 hover:to-violet-700 transition-all flex items-center gap-1.5"
              >
                <span>Sign In</span>
              </a>
            )}
          </div>
        </div>
      </header>

      {/* Main Body Content */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 py-8 flex-1 w-full space-y-8">
        {/* TAB 1: SMART INBOX & REVIEW (PHASE 7) */}
        {activeTab === "inbox" && (
          <div className="space-y-6">
            {/* Header info */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
                  <Inbox className="w-6 h-6 text-indigo-500 dark:text-indigo-400" />
                  <span>Smart Gmail Inbox &amp; Review Studio</span>
                </h1>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                  Unread messages analyzed with local Ollama (<strong className="text-indigo-600 dark:text-indigo-300">{aiHealth?.classifier_model || "phi4-mini:latest"}</strong>).
                  Cryptographic human approval required before sending.
                </p>
              </div>

              {currentUser && (
                <div className="flex items-center gap-3 p-2 px-3 rounded-2xl bg-white/80 border border-slate-200 text-slate-700 shadow-xs dark:bg-slate-900/60 dark:border-slate-800 dark:text-slate-300 text-xs font-mono">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span>{currentUser.email}</span>
                </div>
              )}
            </div>

            {/* Live Inbox Component */}
            <InboxView
              currentUser={currentUser}
              activeModel={aiHealth?.classifier_model || "phi4-mini:latest"}
            />
          </div>
        )}

        {/* TAB 2: AI ENGINE PLAYGROUND (PHASE 4) */}
        {activeTab === "playground" && (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
                <Cpu className="w-6 h-6 text-indigo-500 dark:text-indigo-400" />
                <span>Local AI Engine Live Playground</span>
              </h1>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                Ad-hoc testing for email categorization, importance estimation, and context-aware draft replies.
              </p>
            </div>

            <section className="p-8 rounded-3xl bg-white/85 border border-slate-200 shadow-sm dark:bg-slate-900/40 dark:border-indigo-500/20 backdrop-blur-sm relative overflow-hidden dark:shadow-2xl">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Input Form */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-mono text-slate-600 dark:text-slate-400 mb-1.5">
                      Subject Line
                    </label>
                    <input
                      type="text"
                      value={testSubject}
                      onChange={(e) => setTestSubject(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-300 text-sm text-slate-900 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-mono text-slate-600 dark:text-slate-400 mb-1.5">
                      Sender
                    </label>
                    <input
                      type="text"
                      value={testSender}
                      onChange={(e) => setTestSender(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-300 text-sm text-slate-900 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-mono text-slate-600 dark:text-slate-400 mb-1.5">
                      Email Body
                    </label>
                    <textarea
                      rows={5}
                      value={testBody}
                      onChange={(e) => setTestBody(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-300 text-sm text-slate-900 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 resize-none font-sans dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200"
                    />
                  </div>

                  <div className="flex flex-wrap items-center gap-3 pt-2">
                    <button
                      onClick={handleRunTriage}
                      disabled={aiLoading}
                      className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer shadow-md shadow-indigo-600/20"
                    >
                      <Bot className="w-4 h-4" />
                      <span>{aiLoading ? "Analyzing..." : "Run AI Triage"}</span>
                    </button>

                    <button
                      onClick={handleGenerateDraft}
                      disabled={aiLoading}
                      className="px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer shadow-md shadow-violet-600/20"
                    >
                      <Sparkles className="w-4 h-4" />
                      <span>{aiLoading ? "Drafting..." : "Generate Reply Draft"}</span>
                    </button>
                  </div>

                  {playgroundError && (
                    <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 dark:bg-rose-500/10 dark:border-rose-500/30 dark:text-rose-300 text-xs flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                      <span>{playgroundError}</span>
                    </div>
                  )}
                </div>

                {/* Results Output */}
                <div className="space-y-4">
                  <span className="block text-xs font-mono text-slate-600 dark:text-slate-400">
                    AI Output &bull; Triage &amp; Draft Preview
                  </span>

                  {/* Triage Card */}
                  {triageResult && (
                    <div className="p-4 rounded-2xl bg-white border border-emerald-500/40 dark:bg-slate-950 dark:border-emerald-500/30 space-y-3 shadow-xs animate-in fade-in duration-300">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-mono uppercase tracking-wider text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Classification Result
                        </span>
                        <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                          {triageResult.latency_ms} ms &bull; {triageResult.model_used}
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 text-center text-xs">
                        <div className="p-2 rounded-xl bg-slate-50 border border-slate-200 dark:bg-slate-900 dark:border-slate-800">
                          <span className="text-slate-500 dark:text-slate-400 block text-[10px] uppercase font-mono">
                            Category
                          </span>
                          <span className="font-semibold text-indigo-600 dark:text-indigo-300 uppercase">
                            {triageResult.category}
                          </span>
                        </div>

                        <div className="p-2 rounded-xl bg-slate-50 border border-slate-200 dark:bg-slate-900 dark:border-slate-800">
                          <span className="text-slate-500 dark:text-slate-400 block text-[10px] uppercase font-mono">
                            Importance
                          </span>
                          <span className="font-bold text-amber-600 dark:text-amber-300">
                            {triageResult.importance} / 5
                          </span>
                        </div>

                        <div className="p-2 rounded-xl bg-slate-50 border border-slate-200 dark:bg-slate-900 dark:border-slate-800">
                          <span className="text-slate-500 dark:text-slate-400 block text-[10px] uppercase font-mono">
                            Needs Reply
                          </span>
                          <span className="font-semibold text-emerald-600 dark:text-emerald-300">
                            {triageResult.needs_reply ? "YES" : "NO"}
                          </span>
                        </div>
                      </div>

                      <div className="text-xs text-slate-800 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/60 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800">
                        <strong className="text-slate-900 dark:text-slate-200">Summary: </strong>
                        {triageResult.summary}
                      </div>

                      {triageResult.reasoning_short && (
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          <em>Rationale:</em> {triageResult.reasoning_short}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Draft Card */}
                  {draftResult && (
                    <div className="p-4 rounded-2xl bg-white border border-violet-500/40 dark:bg-slate-950 dark:border-violet-500/30 space-y-3 shadow-xs animate-in fade-in duration-300">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-mono uppercase tracking-wider text-violet-600 dark:text-violet-400 font-semibold flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5" />
                          Suggested Reply (DRAFTED)
                        </span>
                        <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                          {draftResult.latency_ms} ms &bull; {draftResult.tone}
                        </span>
                      </div>

                      <div className="text-xs font-semibold text-slate-900 dark:text-slate-200">
                        {draftResult.subject}
                      </div>

                      <div className="text-xs text-slate-800 dark:text-slate-300 whitespace-pre-wrap bg-slate-50 dark:bg-slate-900/80 p-3 rounded-xl border border-slate-200 dark:border-slate-800 leading-relaxed font-sans">
                        {draftResult.body}
                      </div>

                      <div className="flex items-center justify-between pt-1 text-[11px] font-mono text-slate-500">
                        <span>Zero-Risk: Drafted only, awaits human approval</span>
                        <span className="text-amber-600 dark:text-amber-400/90 font-semibold">Ready for Review</span>
                      </div>
                    </div>
                  )}

                  {!triageResult && !draftResult && (
                    <div className="h-48 border border-dashed border-slate-300 dark:border-slate-800 rounded-2xl flex flex-col items-center justify-center text-center p-6 text-slate-400 dark:text-slate-500">
                      <Bot className="w-8 h-8 mb-2 opacity-50" />
                      <span className="text-xs font-mono">
                        Click &ldquo;Run AI Triage&rdquo; or &ldquo;Generate Reply Draft&rdquo;
                      </span>
                      <span className="text-[11px] text-slate-500 dark:text-slate-600 mt-1">
                        Inference executes locally on your CPU via Ollama
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </section>
          </div>
        )}

        {/* TAB 3: SYSTEM ARCHITECTURE & ROADMAP */}
        {activeTab === "architecture" && (
          <div className="space-y-8">
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
                <ShieldCheck className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                <span>Domain Safety &amp; Implementation Roadmap</span>
              </h1>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                Cryptographic content sealing, MultiFernet vault rotation, and all 7 completed production phases.
              </p>
            </div>

            {/* Live Safety Workflow Visualizer */}
            <section className="p-8 rounded-3xl bg-white/85 border border-slate-200 shadow-sm dark:bg-slate-900/30 dark:border-slate-800/80 backdrop-blur-sm">
              <div className="max-w-2xl mb-8">
                <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white mb-2">
                  Domain-Enforced Draft State Machine (ADR 0003)
                </h2>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Guaranteed by backend business logic. If an approved draft is
                  modified, the hash invalidates and immediately forces re-approval
                  before sending.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-950/60 flex flex-col justify-between shadow-xs">
                  <div>
                    <span className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400 font-semibold uppercase tracking-wider">
                      Step 1
                    </span>
                    <h4 className="font-medium text-slate-900 dark:text-slate-200 mt-1">DRAFTED</h4>
                    <p className="text-xs text-slate-600 dark:text-slate-400 mt-1.5">
                      AI generates suggested reply based on thread context and templates.
                    </p>
                  </div>
                  <div className="mt-4 flex items-center gap-1.5 text-xs text-slate-500 font-mono">
                    <SlidersHorizontal className="w-3.5 h-3.5" />
                    <span>Editable</span>
                  </div>
                </div>

                <div className="p-4 rounded-xl border border-indigo-200 bg-indigo-50/80 text-indigo-900 dark:border-indigo-500/30 dark:bg-indigo-950/20 dark:text-indigo-200 flex flex-col justify-between shadow-xs">
                  <div>
                    <span className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400 font-semibold uppercase tracking-wider">
                      Step 2
                    </span>
                    <h4 className="font-medium text-indigo-950 dark:text-indigo-200 mt-1">APPROVED</h4>
                    <p className="text-xs text-indigo-800/80 dark:text-indigo-300/80 mt-1.5">
                      Human clicks Approve. SHA-256 content hash sealed in database.
                    </p>
                  </div>
                  <div className="mt-4 flex items-center gap-1.5 text-xs text-indigo-600 dark:text-indigo-400 font-mono">
                    <Lock className="w-3.5 h-3.5" />
                    <span>Hash Sealed</span>
                  </div>
                </div>

                <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/80 text-amber-900 dark:border-amber-500/30 dark:bg-amber-950/20 dark:text-amber-200 flex flex-col justify-between shadow-xs">
                  <div>
                    <span className="text-[11px] font-mono text-amber-600 dark:text-amber-400 font-semibold uppercase tracking-wider">
                      Step 3
                    </span>
                    <h4 className="font-medium text-amber-950 dark:text-amber-200 mt-1">SENDING</h4>
                    <p className="text-xs text-amber-800/80 dark:text-amber-300/80 mt-1.5">
                      Hash re-verified, idempotency key locked with FOR UPDATE.
                    </p>
                  </div>
                  <div className="mt-4 flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400 font-mono">
                    <Zap className="w-3.5 h-3.5" />
                    <span>Idempotent</span>
                  </div>
                </div>

                <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/80 text-emerald-900 dark:border-emerald-500/30 dark:bg-emerald-950/20 dark:text-emerald-200 flex flex-col justify-between shadow-xs">
                  <div>
                    <span className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 font-semibold uppercase tracking-wider">
                      Step 4
                    </span>
                    <h4 className="font-medium text-emerald-950 dark:text-emerald-200 mt-1">SENT</h4>
                    <p className="text-xs text-emerald-800/80 dark:text-emerald-300/80 mt-1.5">
                      RFC 5322 MIME message dispatched to Gmail in correct thread.
                    </p>
                  </div>
                  <div className="mt-4 flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 font-mono">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Audited</span>
                  </div>
                </div>
              </div>
            </section>

            {/* System Status & Roadmap Grid */}
            <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* System Environment */}
              <div className="p-6 rounded-2xl bg-white/85 border border-slate-200 shadow-sm dark:bg-slate-900/40 dark:border-slate-800/80">
                <h3 className="font-semibold text-slate-900 dark:text-slate-200 flex items-center gap-2 mb-4">
                  <Server className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
                  <span>Foundation Environment Status</span>
                </h3>
                <ul className="space-y-3 text-xs font-mono">
                  <li className="flex justify-between items-center py-1.5 border-b border-slate-200/80 dark:border-slate-800/60">
                    <span className="text-slate-500 dark:text-slate-400">Backend API</span>
                    <span className="text-slate-900 dark:text-slate-200">
                      FastAPI 0.115 + Python 3.12 (uv)
                    </span>
                  </li>
                  <li className="flex justify-between items-center py-1.5 border-b border-slate-200/80 dark:border-slate-800/60">
                    <span className="text-slate-500 dark:text-slate-400">AI Engine</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                      Ollama ({aiHealth?.classifier_model || "phi4-mini:latest"})
                    </span>
                  </li>
                  <li className="flex justify-between items-center py-1.5 border-b border-slate-200/80 dark:border-slate-800/60">
                    <span className="text-slate-500 dark:text-slate-400">Token Vault</span>
                    <span className="text-slate-900 dark:text-slate-200">MultiFernet Key Rotation</span>
                  </li>
                  <li className="flex justify-between items-center py-1.5">
                    <span className="text-slate-500 dark:text-slate-400">Unit Test Suite</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                      66 / 66 Passing
                    </span>
                  </li>
                </ul>
              </div>

              {/* Phase Roadmap */}
              <div className="p-6 rounded-2xl bg-white/85 border border-slate-200 shadow-sm dark:bg-slate-900/40 dark:border-slate-800/80">
                <h3 className="font-semibold text-slate-900 dark:text-slate-200 flex items-center gap-2 mb-4">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  <span>Implementation Phases &bull; Complete</span>
                </h3>
                <div className="space-y-2.5 text-xs">
                  <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 dark:text-emerald-300">
                    <span>Phase 1: Foundation (Scaffold, Core, Quality Gates)</span>
                    <span className="font-mono font-semibold">COMPLETE</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 dark:text-emerald-300">
                    <span>Phase 2: Database (Models, Alembic, Repositories)</span>
                    <span className="font-mono font-semibold">COMPLETE</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 dark:text-emerald-300">
                    <span>Phase 3: Auth &amp; Google Token Vault</span>
                    <span className="font-mono font-semibold">COMPLETE</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 dark:text-emerald-300">
                    <span>Phase 4: AI Engine (Local Ollama phi4-mini)</span>
                    <span className="font-mono font-semibold">COMPLETE</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 dark:text-emerald-300">
                    <span>Phase 5&ndash;6: Sync, Mailbox &amp; Approval State Machine</span>
                    <span className="font-mono font-semibold">COMPLETE</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 dark:text-emerald-300">
                    <span>Phase 7: Full Inbox &amp; Review Frontend UI</span>
                    <span className="font-mono font-semibold">COMPLETE</span>
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-200/80 dark:border-slate-800/80 py-8 mt-12 text-center text-xs text-slate-500 font-mono">
        <p>
          Mail Agent &bull; Production-Grade Email Management with Domain-Enforced Safety
        </p>
      </footer>
    </div>
  );
}
