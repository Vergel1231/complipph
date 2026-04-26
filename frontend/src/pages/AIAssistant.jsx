import { useState, useRef, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChatCircleDotsIcon, PaperPlaneTiltIcon, SparkleIcon } from "@phosphor-icons/react";
import { toast } from "sonner";

const SUGGESTED = [
  "What's the difference between 8% flat and graduated tax?",
  "When is my next 1701Q deadline?",
  "Do I need to file 2551Q if I'm 8% flat?",
  "How do I compute my net taxable income?",
];

export default function AIAssistant() {
  const [sessionId] = useState(() => `chat-${Date.now()}`);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hi! I'm your BIR tax assistant. Ask me about 1701Q, 2551Q, taxpayer classifications, deadlines, or how to compute your filings.",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async (text) => {
    const message = (text ?? input).trim();
    if (!message || busy) return;
    setMessages((m) => [...m, { role: "user", content: message }]);
    setInput("");
    setBusy(true);
    try {
      const { data } = await api.post("/ai/chat", { session_id: sessionId, message });
      setMessages((m) => [...m, { role: "assistant", content: data.response }]);
    } catch (err) {
      toast.error(formatApiError(err));
      setMessages((m) => [...m, { role: "assistant", content: "Sorry — I had trouble reaching the assistant. Please try again." }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppLayout>
      <div className="mb-8">
        <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-3">Powered by Claude Sonnet 4.5</div>
        <h1 className="font-display font-bold text-olive-900 text-3xl lg:text-5xl tracking-tight">AI Tax Assistant</h1>
        <p className="mt-3 text-sand-700 text-lg max-w-2xl">
          Ask anything about BIR forms, classifications, deadlines, and computations.
        </p>
      </div>

      <div className="bg-white border border-sand-200 rounded-2xl overflow-hidden flex flex-col h-[640px]">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4" data-testid="chat-messages">
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
              {m.role === "assistant" && (
                <div className="h-9 w-9 rounded-md bg-olive-600 grid place-items-center text-white shrink-0">
                  <SparkleIcon size={18} weight="duotone" />
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                  m.role === "user"
                    ? "bg-olive-600 text-white"
                    : "bg-sand-100 text-olive-900 border border-sand-200"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {busy && (
            <div className="flex gap-3">
              <div className="h-9 w-9 rounded-md bg-olive-600 grid place-items-center text-white shrink-0">
                <SparkleIcon size={18} weight="duotone" />
              </div>
              <div className="bg-sand-100 border border-sand-200 rounded-2xl px-4 py-3 text-sm text-sand-700">
                <span className="inline-flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-olive-600 animate-pulse" />
                  <span className="w-2 h-2 rounded-full bg-olive-600 animate-pulse [animation-delay:200ms]" />
                  <span className="w-2 h-2 rounded-full bg-olive-600 animate-pulse [animation-delay:400ms]" />
                </span>
              </div>
            </div>
          )}
        </div>

        {messages.length <= 1 && (
          <div className="px-6 py-4 border-t border-sand-200 bg-sand-50">
            <div className="text-xs uppercase tracking-widest font-bold text-olive-700 mb-3">Try asking</div>
            <div className="flex flex-wrap gap-2">
              {SUGGESTED.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  data-testid={`suggested-prompt-${s.slice(0, 12)}`}
                  className="text-sm px-3 py-1.5 rounded-full bg-white border border-sand-300 text-olive-800 hover:bg-sand-200 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <form
          onSubmit={(e) => { e.preventDefault(); send(); }}
          className="p-4 border-t border-sand-200 flex gap-2 bg-white"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your BIR filing..."
            data-testid="chat-input"
            className="flex-1 bg-white border-sand-300 py-6"
            disabled={busy}
          />
          <Button
            type="submit"
            disabled={busy || !input.trim()}
            data-testid="chat-send-button"
            className="bg-olive-600 hover:bg-olive-700 text-white px-5"
          >
            <PaperPlaneTiltIcon size={18} weight="bold" />
          </Button>
        </form>
      </div>
    </AppLayout>
  );
}
