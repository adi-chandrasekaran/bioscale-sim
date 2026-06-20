import { useEffect, useMemo, useRef, useState } from "react";
import type { SimulationResult } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type AskAIPanelProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  result: SimulationResult | null;
};

function buildContext(result: SimulationResult | null) {
  if (!result) return {};
  return {
    simulation_input: result.simulation_input,
    research_summary: result.research_summary,
    disease_discovery: {
      label: result.disease_discovery.label,
      summary: result.disease_discovery.summary,
      candidates: result.disease_discovery.candidates.slice(0, 5).map((candidate) => ({
        symbol: candidate.symbol,
        score: candidate.score,
        summary: candidate.summary,
        reasons: candidate.reasons,
      })),
    },
    mutation_result: {
      gene: result.mutation_result.gene,
      mutation: result.mutation_result.mutation,
      kind: result.mutation_result.kind,
      amino_acid_change: result.mutation_result.amino_acid_change,
      clinvar_classification: result.mutation_result.clinvar_classification,
      summary: result.mutation_result.summary,
    },
    protein_effect: {
      gene: result.protein_effect.gene,
      protein_name: result.protein_effect.protein_name,
      protein_id: result.protein_effect.protein_id,
      function_summary: result.protein_effect.function_summary,
      domain_hit: result.protein_effect.domain_hit,
      activity: result.protein_effect.activity,
      stability: result.protein_effect.stability,
      binding: result.protein_effect.binding,
      loss_of_function_score: result.protein_effect.loss_of_function_score,
    },
    pathway_result: {
      selected_pathway_name: result.pathway_result.selected_pathway_name,
      selected_pathway_id: result.pathway_result.selected_pathway_id,
      summary: result.pathway_result.summary,
      explanation: result.pathway_result.explanation,
      changed_nodes: result.pathway_result.changed_nodes,
    },
    cell_phenotype: result.cell_phenotype,
    population_result: result.population_result,
    ecosystem_result: result.ecosystem_result,
  };
}

export function AskAIPanel({ open, onOpenChange, result }: AskAIPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Ask me about the current simulation, the biology behind a term, or how to interpret a score.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiStatus, setAiStatus] = useState<{ configured: boolean; provider: string; model?: string | null; message: string } | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  const context = useMemo(() => buildContext(result), [result]);
  const contextKey = useMemo(() => result?.research_summary ?? "empty", [result?.research_summary]);

  useEffect(() => {
    setMessages([
      {
        role: "assistant",
        content: result
          ? "Ask me about the current simulation, the biology behind a term, or how to interpret a score."
          : "Ask me about the simulator, and I will explain the concepts once a run is available.",
      },
    ]);
    setInput("");
    setError(null);
  }, [contextKey]);

  useEffect(() => {
    if (!open) return;
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, open]);

  useEffect(() => {
    if (!open || aiStatus || statusLoading) return;
    let cancelled = false;

    async function loadStatus() {
      setStatusLoading(true);
      try {
        const response = await fetch(`${API_BASE}/api/ai/status`);
        const json = await response.json();
        if (!cancelled && response.ok) {
          setAiStatus(json);
        } else if (!cancelled) {
          setAiStatus({
            configured: false,
            provider: "unavailable",
            model: null,
            message: json.detail ?? "No local LLM is configured on this backend.",
          });
        }
      } catch {
        if (!cancelled) {
          setAiStatus({
            configured: false,
            provider: "unavailable",
            model: null,
            message: "No local LLM is configured on this backend.",
          });
        }
      } finally {
        if (!cancelled) setStatusLoading(false);
      }
    }

    void loadStatus();
    return () => {
      cancelled = true;
    };
  }, [aiStatus, open, statusLoading]);

  const statusLabel = aiStatus
    ? aiStatus.configured
      ? `Connected to Ollama${aiStatus.model ? ` (${aiStatus.model})` : ""}`
      : "Local LLM not configured"
    : statusLoading
      ? "Checking connection…"
      : "Connection unknown";
  const statusClass = aiStatus?.configured ? "connected" : aiStatus ? "unavailable" : "checking";

  async function sendMessage() {
    const question = input.trim();
    if (!question || loading) return;
    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: question }];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history: nextMessages.slice(0, -1), context }),
      });
      const json = await response.json();
      if (!response.ok) throw new Error(json.detail ?? "AI chat failed");
      setMessages((current) => [...current, { role: "assistant", content: json.answer }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI chat failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {!open && (
        <button
          type="button"
          className="askAiButton"
          onClick={() => onOpenChange(true)}
          aria-label="Ask AI"
        >
          ✦ Ask AI
        </button>
      )}
      {open && (
        <aside className="aiDrawer" aria-label="Ask AI panel">
          <div className="aiDrawerHeader">
            <div>
              <p className="aiDrawerEyebrow">Ask AI</p>
              <h3>Simulation tutor</h3>
              <p className="aiDrawerSubtext">Ask about the biology, the math, or how to read a card.</p>
              <div className={`aiStatus ${statusClass}`} aria-live="polite">
                <span className="aiStatusDot" />
                <span>{statusLabel}</span>
              </div>
            </div>
            <button type="button" className="aiDrawerClose" onClick={() => onOpenChange(false)}>
              Close
            </button>
          </div>

          <div className="aiMessages" ref={listRef}>
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={message.role === "user" ? "aiMessage user" : "aiMessage assistant"}>
                {message.content}
              </div>
            ))}
          </div>

          <div className="aiComposer">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about the current simulation..."
              rows={4}
            />
            <div className="aiComposerFooter">
              <span className="aiComposerHint">{loading ? "Thinking…" : "Uses the current simulation context."}</span>
              <button type="button" onClick={() => void sendMessage()} disabled={loading || !input.trim()}>
                Send
              </button>
            </div>
            {error && <p className="aiError">{error}</p>}
          </div>
        </aside>
      )}
    </>
  );
}
