"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import CompanyWarning from "@/components/CompanyWarning";
import DataFreshnessTag from "@/components/DataFreshnessTag";
import { checkBlacklist, suggestCompanies } from "@/lib/api";
import type { BlacklistResult } from "@/lib/api";

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export default function BlacklistPage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<BlacklistResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  // Autocomplete state
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(-1);

  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const debouncedQuery = useDebounce(query, 250);

  // Fetch suggestions when user types
  useEffect(() => {
    if (debouncedQuery.trim().length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    setSuggestLoading(true);
    suggestCompanies(debouncedQuery).then((res) => {
      setSuggestions(res);
      setShowSuggestions(res.length > 0);
      setHighlightIdx(-1);
      setSuggestLoading(false);
    });
  }, [debouncedQuery]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSelect = useCallback((name: string) => {
    setQuery(name);
    setShowSuggestions(false);
    setSuggestions([]);
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showSuggestions || suggestions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIdx((i) => Math.max(i - 1, -1));
    } else if (e.key === "Enter" && highlightIdx >= 0) {
      e.preventDefault();
      handleSelect(suggestions[highlightIdx]);
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
    }
  };

  const handleCheck = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setShowSuggestions(false);
    setLoading(true);
    setSearched(true);
    try {
      const data = await checkBlacklist(query);
      setResult(data);
    } finally {
      setLoading(false);
    }
  };

  // Highlight matched part of suggestion
  const highlight = (name: string, q: string) => {
    const idx = name.toLowerCase().indexOf(q.toLowerCase());
    if (idx === -1) return <span>{name}</span>;
    return (
      <>
        {name.slice(0, idx)}
        <mark className="bg-blue-100 text-blue-800 rounded-sm">{name.slice(idx, idx + q.length)}</mark>
        {name.slice(idx + q.length)}
      </>
    );
  };

  return (
    <div className="page-shell max-w-3xl">
      <div className="mb-6">
        <h1 className="page-title mb-2">Хар жагсаалт шалгах</h1>
        <p className="page-copy">
          НХБХГ болон Мэргэжлийн хяналтын байгууллагын жагсаалтаас компанийн нэрийг шалгана.
        </p>
      </div>

      {/* Search form */}
      <form onSubmit={handleCheck} className="card p-5 mb-6">
        <label className="label">Компанийн нэр</label>
        <div className="relative">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setResult(null);
                  setSearched(false);
                }}
                onKeyDown={handleKeyDown}
                onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                placeholder="Жишээ: Монгол Хаус, Давхар харш..."
                className="input w-full pr-8"
                autoComplete="off"
                id="company-search-input"
              />
              {suggestLoading && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                </div>
              )}

              {/* Dropdown */}
              {showSuggestions && (
                <div
                  ref={dropdownRef}
                  className="absolute top-full left-0 right-0 mt-1 bg-white rounded-xl border border-slate-200 shadow-xl z-50 overflow-hidden max-h-72 overflow-y-auto"
                >
                  <div className="px-3 py-1.5 text-[10px] text-slate-400 border-b border-slate-100 uppercase tracking-wider font-semibold">
                    {suggestions.length} илэрц
                  </div>
                  {suggestions.map((name, i) => (
                    <button
                      key={name}
                      type="button"
                      onMouseDown={() => handleSelect(name)}
                      className={`w-full text-left px-3 py-2.5 text-sm flex items-center gap-2.5 transition-colors ${
                        i === highlightIdx
                          ? "bg-blue-50 text-blue-800"
                          : "text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      <span className="text-slate-400 text-xs shrink-0">🏢</span>
                      <span className="flex-1 min-w-0 truncate">
                        {highlight(name, query)}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button type="submit" className="btn-primary shrink-0" disabled={loading || !query.trim()}>
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Шалгаж байна...
                </span>
              ) : "Шалгах"}
            </button>
          </div>
        </div>
        <p className="text-xs text-slate-400 mt-2">
          ХХК, ХНН гэх дагаврыг оруулахгүй байж болно. Бичиж эхлэхэд санал автоматаар гарна.
        </p>
      </form>

      {/* Result */}
      {searched && !loading && result && (
        <div>
          {result.found ? (
            <CompanyWarning company={result} />
          ) : (
            <div className="card p-5 border-green-200 bg-green-50">
              <div className="flex items-center gap-3">
                <div className="text-3xl">✅</div>
                <div>
                  <div className="font-semibold text-green-900">Олдсонгүй</div>
                  <p className="text-sm text-green-700 mt-0.5">
                    "{query}" нэртэй компани хар жагсаалтад байхгүй байна.
                  </p>
                </div>
              </div>
              <p className="text-xs text-green-600 mt-3">
                ⚠️ Хар жагсаалтад байхгүй нь заавал найдвартай гэсэн баталгаа биш. Гэрээ байгуулахаасаа өмнө мэргэжлийн зөвлөгөө авахыг зөвлөж байна.
              </p>
            </div>
          )}
          <div className="flex justify-end mt-3">
            <DataFreshnessTag date={result.updatedAt} />
          </div>
        </div>
      )}

      {/* Info */}
      <div className="mt-8 space-y-3">
        <h2 className="text-sm font-semibold text-slate-700">Мэдээллийн эх сурвалжууд</h2>
        {[
          { name: "НХБХГ", desc: "Зөвшөөрөлгүй баригдаж буй барилга, ашиглалтад хүлээн аваагүй обьектуудын жагсаалт", badge: "Жил бүр" },
          { name: "Мэргэжлийн хяналт", desc: "Барилга угсралтын дүрэм зөрчсөн, торгуульд өртсөн компаниуд", badge: "Жил бүр" },
          { name: "Улсын бүртгэл", desc: "Татан буугдсан, банкрот зарласан компаниудын мэдээлэл", badge: "Тогтмол" },
        ].map((s) => (
          <div key={s.name} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
            <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 font-bold text-xs flex items-center justify-center shrink-0">
              {s.name[0]}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-slate-800">{s.name}</div>
              <div className="text-xs text-slate-500 mt-0.5">{s.desc}</div>
            </div>
            <span className="text-xs text-slate-400 whitespace-nowrap">{s.badge}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
