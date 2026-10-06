"use client";

import React, { useState, useEffect } from "react";
import {
  Mail,
  RefreshCw,
  Search,
  Filter,
  Star,
  CheckCircle2,
  Clock,
  Sparkles,
  Lock,
  Send,
  AlertCircle,
  SlidersHorizontal,
  ChevronRight,
  ShieldCheck,
  Bot,
  Zap,
  Tag,
  Check,
  Edit3,
} from "lucide-react";
import { EmailMessage, Draft, SyncResult } from "./types";

interface InboxViewProps {
  currentUser: {
    id: string;
    email: string;
    name: string;
    display_name?: string;
  } | null;
  activeModel: string;
}

const DEFAULT_THEME = {
  bg: "bg-slate-100 dark:bg-slate-500/10",
  text: "text-slate-700 dark:text-slate-400",
  border: "border-slate-200 dark:border-slate-500/20",
};

const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  work: {
    bg: "bg-indigo-50 dark:bg-indigo-500/10",
    text: "text-indigo-700 dark:text-indigo-400",
    border: "border-indigo-200 dark:border-indigo-500/20",
  },
  finance: {
    bg: "bg-emerald-50 dark:bg-emerald-500/10",
    text: "text-emerald-700 dark:text-emerald-400",
    border: "border-emerald-200 dark:border-emerald-500/20",
  },
  personal: {
    bg: "bg-purple-50 dark:bg-purple-500/10",
    text: "text-purple-700 dark:text-purple-400",
    border: "border-purple-200 dark:border-purple-500/20",
  },
  alerts: {
    bg: "bg-rose-50 dark:bg-rose-500/10",
    text: "text-rose-700 dark:text-rose-400",
    border: "border-rose-200 dark:border-rose-500/20",
  },
  newsletters: {
    bg: "bg-cyan-50 dark:bg-cyan-500/10",
    text: "text-cyan-700 dark:text-cyan-400",
    border: "border-cyan-200 dark:border-cyan-500/20",
  },
  promotions: {
    bg: "bg-amber-50 dark:bg-amber-500/10",
    text: "text-amber-700 dark:text-amber-400",
    border: "border-amber-200 dark:border-amber-500/20",
  },
  other: {
    bg: "bg-slate-100 dark:bg-slate-500/10",
    text: "text-slate-700 dark:text-slate-400",
    border: "border-slate-200 dark:border-slate-500/20",
  },
};

function getCategoryTheme(cat: string) {
  return CATEGORY_COLORS[cat?.toLowerCase()] ?? DEFAULT_THEME;
}


export default function InboxView({ currentUser, activeModel }: InboxViewProps) {
  const [emails, setEmails] = useState<EmailMessage[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<EmailMessage | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [needsReplyOnly, setNeedsReplyOnly] = useState<boolean>(false);
  const [minImportance, setMinImportance] = useState<number | null>(null);
  const [loadingEmails, setLoadingEmails] = useState<boolean>(false);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [syncFeedback, setSyncFeedback] = useState<{
    type: "success" | "error" | "info";
    message: string;
  } | null>(null);
  const [triagingId, setTriagingId] = useState<string | null>(null);

  // Draft Studio State
  const [currentDraft, setCurrentDraft] = useState<Draft | null>(null);
  const [draftSubject, setDraftSubject] = useState<string>("");
  const [draftBody, setDraftBody] = useState<string>("");
  const [draftTone, setDraftTone] = useState<string>("professional");
  const [customInstructions, setCustomInstructions] = useState<string>("");
  const [isGeneratingDraft, setIsGeneratingDraft] = useState<boolean>(false);
  const [isApprovingDraft, setIsApprovingDraft] = useState<boolean>(false);
  const [isSendingDraft, setIsSendingDraft] = useState<boolean>(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [draftSuccess, setDraftSuccess] = useState<string | null>(null);

  // Fetch Emails
  const fetchEmails = async () => {
    if (!currentUser) return;
    setLoadingEmails(true);
    try {
      let url = "/api/v1/emails?limit=50";
      if (activeCategory !== "all") url += `&category=${activeCategory}`;
      if (minImportance) url += `&min_importance=${minImportance}`;
      if (needsReplyOnly) url += `&needs_reply=true`;

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setEmails(data.items || []);
        if (data.items?.length > 0 && !selectedEmail) {
          setSelectedEmail(data.items[0]);
        }
      }
    } catch {
      // ignore
    } finally {
      setLoadingEmails(false);
    }
  };

  useEffect(() => {
    fetchEmails();
  }, [currentUser, activeCategory, minImportance, needsReplyOnly]);

  // Fetch drafts when selected email changes
  useEffect(() => {
    async function loadDraftForEmail() {
      if (!selectedEmail || !currentUser) {
        setCurrentDraft(null);
        return;
      }
      setDraftError(null);
      setDraftSuccess(null);
      try {
        const res = await fetch("/api/v1/drafts");
        if (res.ok) {
          const data = await res.json();
          const found = data.items?.find((d: Draft) => d.email_id === selectedEmail.id);
          if (found) {
            setCurrentDraft(found);
            setDraftSubject(found.subject);
            setDraftBody(found.body);
            setDraftTone(found.tone);
          } else {
            setCurrentDraft(null);
            setDraftSubject(`Re: ${selectedEmail.subject}`);
            setDraftBody("");
          }
        }
      } catch {
        setCurrentDraft(null);
      }
    }
    loadDraftForEmail();
  }, [selectedEmail, currentUser]);

  // Sync Mailbox
  const handleSyncMailbox = async () => {
    setSyncing(true);
    setSyncFeedback(null);
    try {
      const res = await fetch("/api/v1/mailboxes/sync?max_messages=10", { method: "POST" });
      if (res.ok) {
        const data: SyncResult = await res.json();
        setSyncFeedback({
          type: "success",
          message: `Synced ${data.synced_count} emails (${data.new_messages} new, ${data.triaged_count} classified with local ${activeModel} in ${(data.duration_ms / 1000).toFixed(1)}s)`,
        });
      } else {
        let errDetail = "Unable to sync inbox.";
        try {
          const err = await res.json();
          errDetail = err.detail || errDetail;
        } catch {
          const raw = await res.text();
          if (raw) errDetail = raw.slice(0, 120);
        }
        setSyncFeedback({
          type: "error",
          message: `Sync note: ${errDetail}`,
        });
      }
    } catch (e: unknown) {
      setSyncFeedback({
        type: "error",
        message: e instanceof Error ? e.message : "Sync error",
      });
    } finally {
      setSyncing(false);
      await fetchEmails();
    }
  };

  // Triage single email on-demand
  const handleTriageEmail = async (emailId: string) => {
    setTriagingId(emailId);
    try {
      const res = await fetch(`/api/v1/emails/${emailId}/triage`, { method: "POST" });
      if (res.ok) {
        const updated: EmailMessage = await res.json();
        setEmails((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
        if (selectedEmail?.id === updated.id) {
          setSelectedEmail(updated);
        }
      }
    } catch {
      // ignore
    } finally {
      setTriagingId(null);
    }
  };

  // Generate Draft
  const handleGenerateDraft = async () => {
    if (!selectedEmail) return;
    setIsGeneratingDraft(true);
    setDraftError(null);
    setDraftSuccess(null);
    try {
      const res = await fetch("/api/v1/drafts/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email_id: selectedEmail.id,
          user_instructions: customInstructions,
          tone: draftTone,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Draft generation failed");
      }
      const data: Draft = await res.json();
      setCurrentDraft(data);
      setDraftSubject(data.subject);
      setDraftBody(data.body);
      setDraftSuccess("Draft generated with local Ollama! Status: DRAFTED (Pending Approval)");
    } catch (e: unknown) {
      setDraftError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setIsGeneratingDraft(false);
    }
  };

  // Edit / Save Draft
  const handleSaveDraft = async () => {
    if (!currentDraft) return;
    try {
      const res = await fetch(`/api/v1/drafts/${currentDraft.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject: draftSubject,
          body: draftBody,
          tone: draftTone,
        }),
      });
      if (!res.ok) throw new Error("Failed to save draft");
      const updated: Draft = await res.json();
      setCurrentDraft(updated);
      setDraftSuccess("Draft saved. Invariant: Status set to DRAFTED (Any prior approval reset).");
    } catch (e: unknown) {
      setDraftError(e instanceof Error ? e.message : "Save failed");
    }
  };

  // Approve Draft (Seals SHA-256)
  const handleApproveDraft = async () => {
    if (!currentDraft) return;
    setIsApprovingDraft(true);
    setDraftError(null);
    setDraftSuccess(null);
    try {
      const res = await fetch(`/api/v1/drafts/${currentDraft.id}/approve`, {
        method: "POST",
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Approval failed");
      }
      const updated: Draft = await res.json();
      setCurrentDraft(updated);
      setDraftSuccess(
        `Approved! Cryptographic SHA-256 hash sealed: ${updated.approved_content_sha256?.substring(0, 16)}...`
      );
    } catch (e: unknown) {
      setDraftError(e instanceof Error ? e.message : "Approval failed");
    } finally {
      setIsApprovingDraft(false);
    }
  };

  // Send Draft (Verify Hash & Send via Gmail)
  const handleSendDraft = async () => {
    if (!currentDraft) return;
    setIsSendingDraft(true);
    setDraftError(null);
    setDraftSuccess(null);
    try {
      const res = await fetch(`/api/v1/drafts/${currentDraft.id}/send`, {
        method: "POST",
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Send failed");
      }
      const updated: Draft = await res.json();
      setCurrentDraft(updated);
      setDraftSuccess("Sent successfully via Gmail API! RFC 5322 MIME message dispatched in-thread.");
    } catch (e: unknown) {
      setDraftError(e instanceof Error ? e.message : "Send failed");
    } finally {
      setIsSendingDraft(false);
    }
  };

  const filteredEmails = emails.filter((e) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      e.subject.toLowerCase().includes(q) ||
      e.sender.toLowerCase().includes(q) ||
      e.snippet.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Top Filter and Sync Action Bar */}
      <div className="p-4 rounded-2xl bg-white/85 border border-slate-200 shadow-sm dark:bg-slate-900/40 dark:border-slate-800/80 backdrop-blur-sm flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 dark:text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search subject, sender, or snippet..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-50 border border-slate-300 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200 dark:placeholder-slate-500"
          />
        </div>

        {/* Filters and Sync Button */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => setNeedsReplyOnly(!needsReplyOnly)}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-colors flex items-center gap-1.5 cursor-pointer ${
              needsReplyOnly
                ? "bg-amber-50 text-amber-700 border-amber-300 shadow-xs dark:bg-amber-500/20 dark:text-amber-300 dark:border-amber-500/40"
                : "bg-white border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Needs Reply</span>
          </button>

          <button
            onClick={() => setMinImportance(minImportance === 4 ? null : 4)}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-colors flex items-center gap-1.5 cursor-pointer ${
              minImportance === 4
                ? "bg-rose-50 text-rose-700 border-rose-300 shadow-xs dark:bg-rose-500/20 dark:text-rose-300 dark:border-rose-500/40"
                : "bg-white border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <Star className="w-3.5 h-3.5" />
            <span>High Priority (4-5★)</span>
          </button>

          <button
            onClick={() => fetchEmails()}
            disabled={loadingEmails}
            title="Refresh inbox"
            className="px-3 py-1.5 rounded-xl bg-white hover:bg-slate-100 disabled:opacity-50 text-slate-700 hover:text-slate-900 text-xs font-semibold flex items-center gap-1.5 border border-slate-200 shadow-xs dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 dark:hover:text-white dark:border-slate-700/80 transition-all cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingEmails ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleSyncMailbox}
            disabled={syncing || !currentUser}
            className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-md shadow-emerald-600/20 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? "animate-spin" : ""}`} />
            <span>{syncing ? "Syncing & Triaging..." : "Sync Gmail Inbox"}</span>
          </button>
        </div>
      </div>

      {/* Sync Status Banner */}
      {syncFeedback && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center justify-between gap-2 shadow-xs animate-in fade-in ${
            syncFeedback.type === "success"
              ? "bg-emerald-50 border-emerald-300 text-emerald-800 dark:bg-emerald-950/40 dark:border-emerald-500/30 dark:text-emerald-300"
              : syncFeedback.type === "error"
              ? "bg-rose-50 border-rose-300 text-rose-800 dark:bg-rose-950/40 dark:border-rose-500/30 dark:text-rose-300"
              : "bg-blue-50 border-blue-300 text-blue-800 dark:bg-blue-950/40 dark:border-blue-500/30 dark:text-blue-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {syncFeedback.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 flex-shrink-0" />
            )}
            <span>{syncFeedback.message}</span>
          </div>
          <button
            onClick={() => setSyncFeedback(null)}
            className="text-[11px] opacity-70 hover:opacity-100 cursor-pointer ml-2 underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Category Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        {["all", "work", "finance", "personal", "alerts", "newsletters", "promotions"].map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-3 py-1.5 rounded-xl font-medium uppercase text-[11px] font-mono tracking-wider transition-all cursor-pointer ${
              activeCategory === cat
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/25"
                : "bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 dark:bg-slate-900/60 dark:border-slate-800 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-800"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Master-Detail Split Pane */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Email List (5 cols) */}
        <div className="lg:col-span-5 space-y-3 max-h-[750px] overflow-y-auto pr-1">
          {loadingEmails ? (
            <div className="p-12 text-center text-slate-500 text-xs font-mono">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 opacity-50" />
              Loading emails...
            </div>
          ) : filteredEmails.length === 0 ? (
            <div className="p-10 rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 text-center text-slate-500 space-y-3 bg-white/40 dark:bg-transparent">
              <Mail className="w-8 h-8 mx-auto opacity-40 text-slate-400" />
              <p className="text-xs">No emails match the selected filters.</p>
              <button
                onClick={handleSyncMailbox}
                disabled={syncing || !currentUser}
                className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-500 transition-colors cursor-pointer"
              >
                Sync with Gmail Now
              </button>
            </div>
          ) : (
            filteredEmails.map((email) => {
              const isSelected = selectedEmail?.id === email.id;
              const catTheme = getCategoryTheme(email.category);

              return (
                <div
                  key={email.id}
                  onClick={() => setSelectedEmail(email)}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer text-left relative overflow-hidden ${
                    isSelected
                      ? "bg-indigo-50/70 border-indigo-500 shadow-md shadow-indigo-500/10 ring-1 ring-indigo-500/30 dark:bg-slate-900 dark:border-indigo-500 dark:ring-indigo-500/30"
                      : "bg-white border-slate-200/90 hover:bg-slate-50/80 hover:border-slate-300 shadow-xs dark:bg-slate-900/40 dark:border-slate-800/80 dark:hover:bg-slate-900/70 dark:hover:border-slate-700"
                  }`}
                >
                  {/* Category and Importance Header */}
                  <div className="flex items-center justify-between mb-2">
                    <span
                      className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-full border font-semibold ${catTheme.bg} ${catTheme.text} ${catTheme.border}`}
                    >
                      {email.category}
                    </span>

                    <div className="flex items-center gap-1.5 text-xs">
                      {email.needs_reply && (
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                          Reply Req
                        </span>
                      )}
                      <div className="flex items-center gap-0.5 text-amber-500 dark:text-amber-400 font-mono text-[11px]">
                        <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                        <span>{email.importance}/5</span>
                      </div>
                    </div>
                  </div>

                  {/* Sender & Subject */}
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100 line-clamp-1 mb-1">
                    {email.subject}
                  </h4>
                  <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-1 mb-2 font-mono">
                    From: {email.sender}
                  </p>

                  {/* Summary / Snippet */}
                  <p className="text-xs text-slate-600 dark:text-slate-300/80 line-clamp-2 leading-relaxed bg-slate-50/80 dark:bg-slate-950/40 p-2 rounded-xl border border-slate-200/70 dark:border-slate-800/60">
                    {email.summary || email.snippet}
                  </p>

                  {/* Timestamp */}
                  <div className="mt-2.5 flex items-center justify-between text-[10px] font-mono text-slate-500 dark:text-slate-500">
                    <span>{new Date(email.received_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    <span className="flex items-center gap-1 text-indigo-600 dark:text-indigo-400 font-medium">
                      <span>View details</span>
                      <ChevronRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Reading Pane & AI Draft Studio (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {selectedEmail ? (
            <div className="space-y-6">
              {/* Email Detail Header Card */}
              <div className="p-6 rounded-3xl bg-white/90 border border-slate-200 shadow-sm dark:bg-slate-900/40 dark:border-slate-800/80 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/80 dark:border-slate-800/80 pb-4">
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono uppercase text-indigo-600 dark:text-indigo-400 font-semibold tracking-wider">
                      Thread: {selectedEmail.gmail_thread_id.substring(0, 16)}...
                    </span>
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">
                      {selectedEmail.subject}
                    </h3>
                  </div>

                  <div className="flex items-center gap-2">
                    {(() => {
                      const theme = getCategoryTheme(selectedEmail.category);
                      return (
                        <span
                          className={`text-xs font-mono uppercase px-2.5 py-1 rounded-full border font-semibold ${theme.bg} ${theme.text} ${theme.border}`}
                        >
                          {selectedEmail.category}
                        </span>
                      );
                    })()}
                    <div className="px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200 dark:bg-slate-950 dark:border-slate-800 font-mono text-xs text-amber-600 dark:text-amber-300 font-bold flex items-center gap-1 shadow-xs">
                      <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                      <span>{selectedEmail.importance}/5</span>
                    </div>
                  </div>
                </div>

                {/* Metadata details */}
                <div className="grid grid-cols-2 gap-2 text-xs font-mono text-slate-600 dark:text-slate-400 bg-slate-50/80 dark:bg-slate-950/60 p-3 rounded-2xl border border-slate-200 dark:border-slate-800/60">
                  <div>
                    <span className="text-slate-500">From: </span>
                    <span className="text-slate-900 dark:text-slate-200">{selectedEmail.sender}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Date: </span>
                    <span className="text-slate-900 dark:text-slate-200">
                      {new Date(selectedEmail.received_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* Ollama Intelligence Summary Box */}
                {selectedEmail.summary ? (
                  <div className="p-3.5 rounded-2xl bg-indigo-50/80 border border-indigo-200 text-indigo-950 dark:bg-indigo-950/20 dark:border-indigo-500/30 dark:text-indigo-300 space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] font-mono text-indigo-800 dark:text-indigo-300 font-semibold">
                      <span className="flex items-center gap-1.5">
                        <Bot className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                        Ollama Local Intelligence Breakdown
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500 dark:text-slate-400">Action: {selectedEmail.suggested_action || "review"}</span>
                        <button
                          onClick={() => handleTriageEmail(selectedEmail.id)}
                          disabled={triagingId === selectedEmail.id}
                          className="px-2 py-0.5 rounded bg-indigo-100 hover:bg-indigo-200 text-indigo-800 dark:bg-indigo-900/60 dark:hover:bg-indigo-800 dark:text-indigo-200 text-[10px] cursor-pointer"
                        >
                          {triagingId === selectedEmail.id ? "Analyzing..." : "Re-Triage"}
                        </button>
                      </div>
                    </div>
                    <p className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-sans">
                      {selectedEmail.summary}
                    </p>
                  </div>
                ) : (
                  <div className="p-3.5 rounded-2xl bg-slate-50 border border-dashed border-slate-300 dark:bg-slate-950/60 dark:border-slate-800 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
                      <Bot className="w-4 h-4 text-slate-500" />
                      <span>Not yet evaluated by local Ollama AI</span>
                    </div>
                    <button
                      onClick={() => handleTriageEmail(selectedEmail.id)}
                      disabled={triagingId === selectedEmail.id}
                      className="px-3 py-1 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                    >
                      <Sparkles className={`w-3.5 h-3.5 ${triagingId === selectedEmail.id ? "animate-spin" : ""}`} />
                      <span>{triagingId === selectedEmail.id ? "Evaluating..." : "Run AI Triage"}</span>
                    </button>
                  </div>
                )}

                {/* Email Body Text */}
                <div className="text-xs text-slate-800 dark:text-slate-300 whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto p-4 rounded-2xl bg-slate-50/80 border border-slate-200 dark:bg-slate-950/80 dark:border-slate-800 font-sans">
                  {selectedEmail.body_text || selectedEmail.snippet}
                </div>
              </div>

              {/* Cryptographic AI Reply Studio (ADR 0003) */}
              <div className="p-6 rounded-3xl bg-white/95 border border-violet-200 shadow-md dark:bg-slate-900/40 dark:border-violet-500/30 space-y-5 relative dark:shadow-xl">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800 gap-2">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-violet-600 dark:text-violet-400" />
                    <h3 className="font-bold text-base text-slate-900 dark:text-white">
                      AI Reply Studio &amp; Approval Seal
                    </h3>
                  </div>

                  {currentDraft ? (
                    <div className="flex items-center gap-2 text-xs font-mono">
                      <span className="text-slate-500">State:</span>
                      <span
                        className={`px-2.5 py-0.5 rounded-full font-semibold border ${
                          currentDraft.status === "APPROVED"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-500/20 dark:text-emerald-300 dark:border-emerald-500/40"
                            : currentDraft.status === "SENT"
                              ? "bg-blue-50 text-blue-700 border-blue-300 dark:bg-blue-500/20 dark:text-blue-300 dark:border-blue-500/40"
                              : "bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-500/20 dark:text-amber-300 dark:border-amber-500/40"
                        }`}
                      >
                        {currentDraft.status}
                      </span>
                    </div>
                  ) : (
                    <span className="text-xs font-mono text-slate-500">No draft created yet</span>
                  )}
                </div>

                {/* Notification messages */}
                {draftSuccess && (
                  <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-800 dark:bg-emerald-500/10 dark:border-emerald-500/30 dark:text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                    <span>{draftSuccess}</span>
                  </div>
                )}
                {draftError && (
                  <div className="p-3 rounded-xl bg-rose-50 border border-rose-300 text-rose-800 dark:bg-rose-500/10 dark:border-rose-500/30 dark:text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{draftError}</span>
                  </div>
                )}

                {/* If draft does not exist: AI Generation Form */}
                {!currentDraft ? (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-mono text-slate-600 dark:text-slate-400 mb-1.5">
                        Steering Guidance / Intent (Optional)
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Accept proposal, confirm Tuesday 2 PM call..."
                        value={customInstructions}
                        onChange={(e) => setCustomInstructions(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-300 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/20 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200 dark:placeholder-slate-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-mono text-slate-600 dark:text-slate-400 mb-1.5">
                        Target Reply Tone
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {["professional", "casual", "concise", "warm"].map((t) => (
                          <button
                            key={t}
                            onClick={() => setDraftTone(t)}
                            className={`px-3 py-1.5 rounded-xl text-xs font-medium border capitalize transition-colors cursor-pointer ${
                              draftTone === t
                                ? "bg-violet-600 text-white border-violet-500 shadow-md shadow-violet-600/25"
                                : "bg-white border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-400 dark:hover:text-white"
                            }`}
                          >
                            {t}
                          </button>
                        ))}
                      </div>
                    </div>

                    <button
                      onClick={handleGenerateDraft}
                      disabled={isGeneratingDraft}
                      className="w-full py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-50 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-md shadow-violet-600/20 transition-all cursor-pointer"
                    >
                      <Sparkles className={`w-4 h-4 ${isGeneratingDraft ? "animate-spin" : ""}`} />
                      <span>{isGeneratingDraft ? "Drafting with Local Ollama..." : "Generate AI Reply Draft"}</span>
                    </button>
                  </div>
                ) : (
                  /* If draft exists: Interactive Editor & Approval Workflow */
                  <div className="space-y-4">
                    {/* Status Alert */}
                    {currentDraft.status === "APPROVED" && (
                      <div className="p-3 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-800 dark:bg-emerald-950/30 dark:border-emerald-500/30 dark:text-emerald-300 text-xs flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Lock className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                          <span>
                            Content Sealed with SHA-256: <code>{currentDraft.approved_content_sha256?.substring(0, 16)}...</code>
                          </span>
                        </div>
                        <span className="text-[10px] font-mono text-emerald-700 dark:text-emerald-400/80 font-bold">Domain Locked</span>
                      </div>
                    )}

                    {currentDraft.status === "DRAFTED" && (
                      <div className="p-3 rounded-2xl bg-amber-50 border border-amber-300 text-amber-800 dark:bg-amber-950/20 dark:border-amber-500/30 dark:text-amber-300 text-xs flex items-center gap-2">
                        <SlidersHorizontal className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                        <span>
                          Human-in-the-loop: Review and approve the suggested draft before dispatching.
                        </span>
                      </div>
                    )}

                    {currentDraft.status === "SENT" && (
                      <div className="p-3 rounded-2xl bg-blue-50 border border-blue-300 text-blue-800 dark:bg-blue-950/20 dark:border-blue-500/30 dark:text-blue-300 text-xs flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                        <span>
                          Message was dispatched to Gmail. ID: {currentDraft.gmail_message_id}
                        </span>
                      </div>
                    )}

                    <div>
                      <label className="block text-xs font-mono text-slate-600 dark:text-slate-400 mb-1">
                        Reply Subject
                      </label>
                      <input
                        type="text"
                        value={draftSubject}
                        disabled={currentDraft.status === "SENT"}
                        onChange={(e) => setDraftSubject(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/20 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-mono text-slate-600 dark:text-slate-400 mb-1">
                        Reply Body
                      </label>
                      <textarea
                        rows={6}
                        value={draftBody}
                        disabled={currentDraft.status === "SENT"}
                        onChange={(e) => setDraftBody(e.target.value)}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/20 resize-none font-sans dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200"
                      />
                    </div>

                    {/* Action Buttons for the State Machine */}
                    <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                      {currentDraft.status !== "SENT" && (
                        <button
                          onClick={handleSaveDraft}
                          className="px-3.5 py-2 rounded-xl border border-slate-300 hover:border-slate-400 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs dark:border-slate-800 dark:hover:border-slate-700 dark:bg-slate-950 dark:text-slate-300"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                          <span>Save Edits</span>
                        </button>
                      )}

                      <div className="flex items-center gap-2.5 ml-auto">
                        {currentDraft.status === "DRAFTED" && (
                          <button
                            onClick={handleApproveDraft}
                            disabled={isApprovingDraft}
                            className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-emerald-600/20 transition-all cursor-pointer"
                          >
                            <ShieldCheck className="w-4 h-4" />
                            <span>{isApprovingDraft ? "Sealing..." : "Approve & Seal (SHA-256)"}</span>
                          </button>
                        )}

                        {currentDraft.status === "APPROVED" && (
                          <button
                            onClick={handleSendDraft}
                            disabled={isSendingDraft}
                            className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-emerald-600/25 transition-all cursor-pointer animate-pulse"
                          >
                            <Send className="w-4 h-4" />
                            <span>{isSendingDraft ? "Verifying & Sending..." : "Send via Gmail"}</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="p-16 rounded-3xl border border-dashed border-slate-300 dark:border-slate-800 text-center text-slate-500 flex flex-col items-center justify-center bg-white/40 dark:bg-transparent">
              <Mail className="w-10 h-10 mb-3 opacity-30 text-indigo-500 dark:text-indigo-400" />
              <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Select an email to view intelligence &amp; draft reply</p>
              <p className="text-xs text-slate-500 mt-1">
                Local Ollama AI evaluates priority, highlights reply needs, and drafts responses.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
