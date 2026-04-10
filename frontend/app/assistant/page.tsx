"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import GlassCard from "@/components/GlassCard";
import { useAuth } from "@/contexts/AuthContext";
import { useAnalytics } from "@/components/AnalyticsProvider";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTED_PROMPTS = [
  "What audience segments do we have for Food & Drink?",
  "How does our 1st party data targeting work?",
  "What are the SLAs for audience requests?",
];

export default function AssistantPage() {
  const { user, loading } = useAuth();
  const { track } = useAnalytics();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login?redirect=/assistant");
    }
  }, [user, loading, router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  async function sendMessage(text: string) {
    if (!text.trim() || isStreaming) return;

    const userMessage: Message = { role: "user", content: text.trim() };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setIsStreaming(true);
    setStatus(null);

    track("Assistant Message Sent", { message_length: text.trim().length });

    // Build the messages array for the API (only role + content)
    const apiMessages = newMessages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const response = await fetch("/api/assistant/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ messages: apiMessages }),
      });

      if (!response.ok) {
        throw new Error("Request failed: " + response.status);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let assistantContent = "";

      // Add empty assistant message to fill in
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            if (event.type === "content") {
              assistantContent += event.text;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: assistantContent,
                };
                return updated;
              });
            } else if (event.type === "status") {
              setStatus(event.message);
            } else if (event.type === "done") {
              setStatus(null);
            } else if (event.type === "error") {
              assistantContent +=
                "\n\nSorry, something went wrong. Please try again.";
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: assistantContent,
                };
                return updated;
              });
            }
          } catch {
            // skip malformed JSON
          }
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          role: "assistant",
          content: "Sorry, I couldn't connect to the server. Please try again.",
        },
      ]);
    } finally {
      setIsStreaming(false);
      setStatus(null);
      inputRef.current?.focus();
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    sendMessage(input);
  }

  function handlePromptClick(prompt: string) {
    sendMessage(prompt);
  }

  if (loading || !user) {
    return null;
  }

  const showPromptCards = messages.length === 0;

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0c10]">
      <Navbar />

      <main className="flex-1 flex flex-col pt-24 pb-24 max-w-4xl mx-auto w-full px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white font-headline tracking-tight">
            Prism Assistant
          </h1>
          <p className="text-slate-400 mt-2">
            Ask me anything about our data products and audience segments.
          </p>
        </div>

        {/* Prompt cards (welcome state) */}
        {showPromptCards && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            {SUGGESTED_PROMPTS.map((prompt, i) => (
              <button
                key={i}
                onClick={() => handlePromptClick(prompt)}
                className="glass-card rounded-2xl p-5 border border-white/10 shadow-2xl
                  text-left text-sm text-slate-300 hover:text-white
                  hover:border-accent-cyan/30 hover:shadow-[0_0_20px_rgba(31,137,223,0.15)]
                  transition-all duration-300 cursor-pointer"
              >
                {prompt}
              </button>
            ))}
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 space-y-4 overflow-y-auto">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start items-start gap-3"}`}
            >
              {msg.role === "assistant" && (
                <img
                  src="/prism-assistant-avatar.png"
                  alt="Prism Assistant"
                  className="w-8 h-8 rounded-full flex-shrink-0 mt-1"
                />
              )}
              <div
                className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                  msg.role === "user"
                    ? "bg-accent-cyan/15 border border-accent-cyan/20 text-white"
                    : "glass-card border border-white/10 text-slate-200"
                }`}
              >
                {msg.role === "assistant" ? (
                  <div className="text-sm text-slate-200 space-y-3">
                    {(msg.content || "...").split("\n").map((line, j) =>
                      line.trim() ? (
                        <div key={j} className="prose prose-invert prose-sm max-w-none [&>p]:m-0">
                          <ReactMarkdown>{line}</ReactMarkdown>
                        </div>
                      ) : (
                        <div key={j} className="h-1" />
                      )
                    )}
                  </div>
                ) : (
                  <p className="text-sm">{msg.content}</p>
                )}
              </div>
            </div>
          ))}

          {/* Status indicator */}
          {status && (
            <div className="flex justify-start">
              <div className="glass-card rounded-2xl px-5 py-3 border border-white/10 text-accent-cyan text-sm flex items-center gap-2">
                <span className="w-2 h-2 bg-accent-cyan rounded-full animate-pulse" />
                {status}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Fixed input bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-[#0a0c10]/90 backdrop-blur-[20px] border-t border-white/5 p-4">
        <form
          onSubmit={handleSubmit}
          className="max-w-4xl mx-auto flex items-center gap-3"
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about segments, targeting, SLAs..."
            disabled={isStreaming}
            className="flex-1 bg-surface-container rounded-xl px-5 py-3 text-white text-sm
              placeholder:text-slate-500 border border-white/10
              focus:outline-none focus:ring-2 focus:ring-accent-cyan/50 focus:border-accent-cyan/30
              disabled:opacity-50 transition-all"
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="refractive-gradient px-6 py-3 rounded-xl font-bold text-white text-sm
              shadow-lg active:scale-95 transition-transform
              disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isStreaming ? "..." : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}
