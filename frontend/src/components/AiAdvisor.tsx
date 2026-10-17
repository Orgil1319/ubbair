"use client";

import { useState, useRef, useEffect } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  propertyId: string;
  propertyTitle: string;
  riskScore?: number;
}

export default function AiAdvisor({ propertyId, propertyTitle, riskScore }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: `Сайн байна уу! Би таны **${propertyTitle}** байрыг сонгоход туслах зөвлөгч. Эрсдэлийн оноо: **${riskScore ?? "—"}/100**.\n\nЯмар асуулт байна вэ? Жишээ нь:\n- "Энэ байрны үерийн эрсдэл хэр их вэ?"\n- "Гэрээнд ямар заалт оруулах хэрэгтэй вэ?"\n- "Барилгын компани нь найдвартай юу?"\n\n*Санамж: Энэхүү систем нь зөвхөн зөвлөх зорилготой бөгөөд хуулийн баталгаа болохгүй.*`,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = { role: "user", content: text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          property_id: propertyId,
          property_context: {
            propertyId,
            propertyTitle,
            riskScore: riskScore ?? null,
          },
          messages: [...messages, userMsg].map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setMessages((m) => [...m, { role: "assistant", content: body?.detail ?? "Алдаа гарлаа. Дахин оролдоно уу." }]);
        return;
      }

      const data = await res.json();
      setMessages((m) => [...m, { role: "assistant", content: data.response ?? "Алдаа гарлаа." }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "Алдаа гарлаа. Дахин оролдоно уу." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="card flex flex-col h-[480px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-sm">🤖</div>
        <div>
          <div className="text-sm font-medium text-slate-900">AI Зөвлөгч</div>
          <div className="text-xs text-slate-500">Байрны эрсдэл, хуулийн асуулт</div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
              m.role === "user"
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-800"
            }`}>
              {m.content.split("\n").map((line, j) => (
                <span key={j}>
                  {line.replace(/\*\*(.*?)\*\*/g, (_, t) => t)}
                  {j < m.content.split("\n").length - 1 && <br />}
                </span>
              ))}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-100 rounded-xl px-4 py-3 text-sm text-slate-500">
              <span className="inline-flex gap-1">
                <span className="animate-bounce" style={{ animationDelay: "0ms" }}>•</span>
                <span className="animate-bounce" style={{ animationDelay: "150ms" }}>•</span>
                <span className="animate-bounce" style={{ animationDelay: "300ms" }}>•</span>
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-100 p-3 flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Асуулт бичнэ үү... (Enter илгээх)"
          className="flex-1 resize-none input py-2 text-sm h-10 max-h-24"
          rows={1}
        />
        <button
          onClick={send}
          disabled={!input.trim() || loading}
          className="btn-primary px-3 py-2 shrink-0"
        >
          ↑
        </button>
      </div>
    </div>
  );
}
