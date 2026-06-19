"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useRef, useEffect, useCallback } from "react";
import {
  X, Send, Bot, Sparkles, Minimize2, Maximize2,
  RefreshCw, Globe, Database, AlertCircle,
} from "lucide-react";
import { getToken } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────
interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface EstimateContext {
  estimateId?: string | number;
  customerName?: string;
  version?: string;
  awsMonthlyCost?: number;
  gcpMonthlyCost?: number;
  aws5YearTCO?: number;
  clientMode?: string;
  dbType?: string;
  cloudProviders?: string[];
  environments?: Record<string, any>;
  metrics?: Record<string, any>;
}

interface AICopilotProps {
  estimateContext?: EstimateContext;
  defaultVisible?: boolean;
  suggestedPrompts?: string[];
}

// ── Global event bus — lets any page open the copilot + send a message ─────────
export function openCopilotWithPrompt(prompt: string) {
  window.dispatchEvent(new CustomEvent("copilot:send", { detail: { prompt } }));
}
export function openCopilot() {
  window.dispatchEvent(new CustomEvent("copilot:open"));
}

// ── Suggested prompts ──────────────────────────────────────────────────────────
const GLOBAL_PROMPTS = [
  "Which estimate has the highest monthly cost?",
  "Compare AWS vs GCP costs across all estimates",
  "How can I reduce cloud costs across all clients?",
  "What is the average infrastructure cost per user?",
  "Show me cost optimization opportunities",
];

const ESTIMATE_PROMPTS = [
  "Summarize this estimate's cost breakdown",
  "How does AWS compare to GCP for this estimate?",
  "What's the 5-year TCO for this workload?",
  "Where are the biggest cost drivers?",
  "How can I reduce this estimate's monthly cost?",
];

// ── API call ───────────────────────────────────────────────────────────────────
async function callCopilotAPI(
  question: string,
  context?: EstimateContext,
  allEstimates?: any[]
): Promise<string> {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const token   = getToken();

  try {
    const res = await fetch(`${apiBase}/api/copilot/chat`, {
      method:  "POST",
      headers: {
        "Content-Type":  "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        question,
        estimate_context: context || null,
        all_estimates:    allEstimates || [],
      }),
    });
    if (res.ok) {
      const data = await res.json();
      return data.answer || "I couldn't generate a response. Please try again.";
    }
  } catch {}
  return generateFallbackResponse(question, context);
}

function generateFallbackResponse(question: string, ctx?: EstimateContext): string {
  const q = question.toLowerCase();
  if (ctx) {
    const monthly = ctx.awsMonthlyCost ? `$${ctx.awsMonthlyCost.toLocaleString()}` : "N/A";
    if (q.includes("cost") || q.includes("breakdown") || q.includes("summary")) {
      return `**${ctx.customerName || "Estimate"} (${ctx.version || "V1"}) — Cost Summary**\n\n` +
        `• **Monthly (AWS):** ${monthly}\n• **Monthly (GCP):** ${ctx.gcpMonthlyCost ? "$" + ctx.gcpMonthlyCost.toLocaleString() : "N/A"}\n• **5-Year TCO:** ${ctx.aws5YearTCO ? "$" + ctx.aws5YearTCO.toLocaleString() : "N/A"}\n• **Mode:** ${ctx.clientMode === "saas" ? "SaaS / Cloud" : "On-Premise"}\n• **Database:** ${ctx.dbType || "PostgreSQL"}\n\nWould you like a deeper breakdown by environment?`;
    }
  }
  return `I'm your **AI Cost Copilot**. Configure GROQ_API_KEY in .env for full AI responses.`;
}

// ── Markdown renderer ──────────────────────────────────────────────────────────
function renderContent(content: string) {
  const lines = content.split("\n");
  return lines.map((line, i) => {
    const boldified = line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    const isBullet  = line.startsWith("• ") || line.startsWith("- ") || /^\d+\./.test(line);
    const isHeader  = line.startsWith("### ") || line.startsWith("## ") || line.startsWith("# ");
    if (isHeader) {
      const text = line.replace(/^#+\s/, "");
      return (
        <span key={i}>
          <strong dangerouslySetInnerHTML={{ __html: text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") }} />
          <br />
        </span>
      );
    }
    return (
      <span key={i}>
        {isBullet ? (
          <span className="flex items-start gap-1.5 mb-1">
            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-current flex-shrink-0 opacity-50" />
            <span dangerouslySetInnerHTML={{ __html: boldified.replace(/^[•\-]\s/, "").replace(/^\d+\.\s/, "") }} />
          </span>
        ) : (
          <span dangerouslySetInnerHTML={{ __html: boldified }} />
        )}
        {i < lines.length - 1 && !isBullet && !isHeader && line !== "" && <br />}
        {line === "" && i < lines.length - 1 && <br />}
      </span>
    );
  });
}

// ── Main Component ─────────────────────────────────────────────────────────────
export default function AICopilot({
  estimateContext,
  defaultVisible = true,
  suggestedPrompts,
}: AICopilotProps) {
  const [isOpen,       setIsOpen]       = useState(false);
  const [isMin,        setIsMin]        = useState(false);
  const [messages,     setMessages]     = useState<Message[]>([]);
  const [input,        setInput]        = useState("");
  const [isTyping,     setIsTyping]     = useState(false);
  const [allEstimates, setAllEstimates] = useState<any[]>([]);

  // FAB drag position
  const [fabPos, setFabPos] = useState({ x: 0, y: 0 });
  const isDragging          = useRef(false);
  const dragStart           = useRef({ mx: 0, my: 0, bx: 0, by: 0 });
  const messagesEndRef      = useRef<HTMLDivElement>(null);
  // Queue a message to send once the drawer + greeting are ready
  const pendingPromptRef    = useRef<string | null>(null);

  const prompts = suggestedPrompts || (estimateContext ? ESTIMATE_PROMPTS : GLOBAL_PROMPTS);

  // ── Load all estimates ───────────────────────────────────────────────────────
  useEffect(() => {
    const token = getToken();
    if (!estimateContext) {
      fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/all-estimates`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
        .then((r) => r.ok ? r.json() : [])
        .then((ests: any[]) => setAllEstimates(ests))
        .catch(() => {});
    }
  }, [estimateContext]);

  // ── Global event listeners ───────────────────────────────────────────────────
  useEffect(() => {
    const handleOpen = () => setIsOpen(true);
    const handleSend = (e: Event) => {
      const prompt = (e as CustomEvent<{ prompt: string }>).detail.prompt;
      pendingPromptRef.current = prompt;
      setIsOpen(true);
    };
    window.addEventListener("copilot:open", handleOpen);
    window.addEventListener("copilot:send", handleSend);
    return () => {
      window.removeEventListener("copilot:open", handleOpen);
      window.removeEventListener("copilot:send", handleSend);
    };
  }, []);

  // ── Greeting on open ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const greeting: Message = {
        id:        "welcome",
        role:      "assistant",
        content:   estimateContext
          ? `👋 Hi! I'm your **AI Cost Copilot** for **${estimateContext.customerName || "this estimate"} ${estimateContext.version || ""}**.\n\nI have full context of this estimate — ask me anything about costs, comparisons, or optimization opportunities.`
          : `👋 Hi! I'm your **AI Cost Copilot**.\n\nI have access to **${allEstimates.length} estimates** across your clients. Ask me anything about cloud costs, comparisons, or savings opportunities!`,
        timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages([greeting]);
    }
  }, [isOpen]);

  // ── Fire pending prompt after greeting is set ────────────────────────────────
  useEffect(() => {
    if (isOpen && messages.length > 0 && pendingPromptRef.current) {
      const prompt = pendingPromptRef.current;
      pendingPromptRef.current = null;
      // Small delay so the user sees the greeting first
      setTimeout(() => sendMessage(prompt), 350);
    }
  }, [isOpen, messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // ── Draggable FAB ────────────────────────────────────────────────────────────
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    isDragging.current = false;
    dragStart.current  = { mx: e.clientX, my: e.clientY, bx: fabPos.x, by: fabPos.y };
    const onMove = (ev: MouseEvent) => {
      const dx = ev.clientX - dragStart.current.mx;
      const dy = ev.clientY - dragStart.current.my;
      if (Math.abs(dx) > 4 || Math.abs(dy) > 4) isDragging.current = true;
      setFabPos({ x: dragStart.current.bx + dx, y: dragStart.current.by + dy });
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, [fabPos]);

  const onTouchStart = useCallback((e: React.TouchEvent) => {
    const touch = e.touches[0];
    isDragging.current = false;
    dragStart.current  = { mx: touch.clientX, my: touch.clientY, bx: fabPos.x, by: fabPos.y };
    const onMove = (ev: TouchEvent) => {
      const t  = ev.touches[0];
      const dx = t.clientX - dragStart.current.mx;
      const dy = t.clientY - dragStart.current.my;
      if (Math.abs(dx) > 4 || Math.abs(dy) > 4) isDragging.current = true;
      setFabPos({ x: dragStart.current.bx + dx, y: dragStart.current.by + dy });
    };
    const onUp = () => {
      document.removeEventListener("touchmove", onMove);
      document.removeEventListener("touchend", onUp);
    };
    document.addEventListener("touchmove", onMove, { passive: true });
    document.addEventListener("touchend", onUp);
  }, [fabPos]);

  const handleFabClick = () => {
    if (!isDragging.current) setIsOpen(true);
  };

  // ── Send message ─────────────────────────────────────────────────────────────
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isTyping) return;
    const userMsg: Message = {
      id:        Date.now().toString(),
      role:      "user",
      content:   text,
      timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    const answer = await callCopilotAPI(text, estimateContext, allEstimates);
    const assistantMsg: Message = {
      id:        (Date.now() + 1).toString(),
      role:      "assistant",
      content:   answer,
      timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, assistantMsg]);
    setIsTyping(false);
  }, [isTyping, estimateContext, allEstimates]);

  const clearChat = () => setMessages([]);

  // ── Context badge ─────────────────────────────────────────────────────────────
  const contextBadge = estimateContext ? (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-violet-100 text-violet-700 border border-violet-200">
      <Database className="w-2.5 h-2.5" />
      {estimateContext.customerName} {estimateContext.version}
    </div>
  ) : (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-700 border border-emerald-200">
      <Globe className="w-2.5 h-2.5" />
      All Estimates ({allEstimates.length})
    </div>
  );

  return (
    <>
      {/* ── Draggable FAB ──────────────────────────────────────────────────────── */}
      <motion.button
        id="copilot-fab"
        data-copilot-fab
        onMouseDown={onMouseDown}
        onTouchStart={onTouchStart}
        onClick={handleFabClick}
        animate={{ x: fabPos.x, y: fabPos.y }}
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.95 }}
        className="fixed bottom-6 right-6 w-14 h-14 rounded-2xl flex items-center justify-center shadow-2xl z-50 cursor-grab active:cursor-grabbing select-none"
        style={{ background: "linear-gradient(135deg, #2563eb, #7c3aed)", touchAction: "none" }}
        title="Drag to move · Click to open"
      >
        <Bot className="w-6 h-6 text-white pointer-events-none" />
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-400 rounded-full border-2 border-white flex items-center justify-center">
          <span className="w-1.5 h-1.5 bg-white rounded-full animate-ping" />
        </span>
      </motion.button>

      {/* ── Drawer ─────────────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 0.25 }} exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 bg-black z-40"
            />

            {/* Drawer panel */}
            <motion.div
              initial={{ x: "100%", opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: "100%", opacity: 0 }}
              transition={{ type: "spring", damping: 28, stiffness: 280 }}
              className={`fixed right-0 top-0 h-full bg-white shadow-2xl z-50 flex flex-col transition-all duration-200 ${isMin ? "w-80" : "w-[460px]"}`}
            >
              {/* Header */}
              <div
                className="flex items-center gap-3 px-5 py-4 border-b border-white/10 flex-shrink-0"
                style={{ background: "linear-gradient(135deg, #0f1729, #1a2540)" }}
              >
                <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: "linear-gradient(135deg, #2563eb, #7c3aed)" }}>
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white font-bold text-sm">AI Cost Copilot</p>
                  <div className="flex items-center gap-2 mt-0.5">{contextBadge}</div>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={clearChat} className="p-1.5 rounded-lg hover:bg-white/10 transition-colors" title="Clear chat">
                    <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
                  </button>
                  <button onClick={() => setIsMin(!isMin)} className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                    {isMin ? <Maximize2 className="w-3.5 h-3.5 text-slate-400" /> : <Minimize2 className="w-3.5 h-3.5 text-slate-400" />}
                  </button>
                  <button onClick={() => setIsOpen(false)} className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                    <X className="w-4 h-4 text-slate-400" />
                  </button>
                </div>
              </div>

              {/* Quick prompts */}
              {!isMin && (
                <div className="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-blue-50 flex-shrink-0">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
                    {estimateContext ? "Ask about this estimate" : "Try asking"}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {prompts.slice(0, 4).map((p, i) => (
                      <button key={i} onClick={() => sendMessage(p)}
                        className="text-[11px] px-2.5 py-1.5 rounded-lg bg-white text-blue-700 hover:bg-blue-50 transition-colors border border-blue-200 font-medium shadow-sm"
                      >{p}</button>
                    ))}
                  </div>
                </div>
              )}

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0">
                {messages.length === 0 && (
                  <div className="text-center py-12">
                    <div className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center"
                      style={{ background: "linear-gradient(135deg, #2563eb20, #7c3aed20)" }}>
                      <Bot className="w-7 h-7 text-violet-500" />
                    </div>
                    <p className="text-sm font-semibold text-slate-700">Ask me anything</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {estimateContext
                        ? `Full context loaded for ${estimateContext.customerName}`
                        : "I can access all your estimates across all clients"}
                    </p>
                  </div>
                )}

                {messages.map((msg) => (
                  <motion.div key={msg.id}
                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                    className={`flex gap-2.5 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                  >
                    {msg.role === "assistant" && (
                      <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                        style={{ background: "linear-gradient(135deg, #2563eb, #7c3aed)" }}>
                        <Bot className="w-3.5 h-3.5 text-white" />
                      </div>
                    )}
                    <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                      msg.role === "user" ? "text-white" : "bg-slate-100 text-slate-800"
                    }`}
                      style={msg.role === "user" ? { background: "linear-gradient(135deg, #2563eb, #7c3aed)" } : {}}
                    >
                      <div className="whitespace-pre-wrap">{renderContent(msg.content)}</div>
                      <p className={`text-[10px] mt-1.5 ${msg.role === "user" ? "text-white/60" : "text-slate-400"}`}>
                        {msg.timestamp}
                      </p>
                    </div>
                  </motion.div>
                ))}

                {isTyping && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-2.5">
                    <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                      style={{ background: "linear-gradient(135deg, #2563eb, #7c3aed)" }}>
                      <Bot className="w-3.5 h-3.5 text-white" />
                    </div>
                    <div className="bg-slate-100 rounded-2xl px-4 py-3 flex gap-1 items-center">
                      {[0, 1, 2].map((i) => (
                        <motion.div key={i} className="w-1.5 h-1.5 bg-slate-400 rounded-full"
                          animate={{ y: [0, -5, 0] }}
                          transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.12 }} />
                      ))}
                    </div>
                  </motion.div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="px-4 py-4 border-t border-slate-100 flex-shrink-0 bg-white">
                {estimateContext && (
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mb-2">
                    <AlertCircle className="w-3 h-3" />
                    Context: {estimateContext.customerName} · AWS ${estimateContext.awsMonthlyCost?.toLocaleString() || "N/A"}/mo
                  </div>
                )}
                <div className="flex gap-2">
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage(input)}
                    placeholder={estimateContext ? "Ask about this estimate..." : "Ask about your estimates..."}
                    className="flex-1 px-3.5 py-2.5 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 bg-slate-50 transition-all"
                    disabled={isTyping}
                    autoFocus={isOpen}
                  />
                  <motion.button
                    onClick={() => sendMessage(input)}
                    disabled={!input.trim() || isTyping}
                    whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                    className="w-10 h-10 rounded-xl flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ background: "linear-gradient(135deg, #2563eb, #7c3aed)" }}
                  >
                    <Send className="w-4 h-4 text-white" />
                  </motion.button>
                </div>
                <p className="text-[10px] text-slate-400 text-center mt-2">
                  Powered by Groq LLaMA 3.3 · BusinessNext AI
                </p>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
