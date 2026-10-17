"use client";

import { useState } from "react";

interface DiaryEntry {
  id: string;
  date: string;
  title: string;
  description: string;
  images: string[];
  category: "issue" | "repair" | "note";
}

const MOCK_ENTRIES: DiaryEntry[] = [
  {
    id: "1",
    date: "2025-05-08",
    title: "Гал тогооны усны цорго гоожиж байна",
    description: "Байрны эзэнд мэдэгдсэн. Засах болно гэсэн ч одоохондоо хариу өгөөгүй.",
    images: [],
    category: "issue",
  },
];

const CATEGORY_LABELS = {
  issue: { label: "Доголдол", color: "bg-red-100 text-red-700" },
  repair: { label: "Засвар", color: "bg-green-100 text-green-700" },
  note: { label: "Тэмдэглэл", color: "bg-blue-100 text-blue-700" },
};

export default function DiaryPage() {
  const [entries, setEntries] = useState<DiaryEntry[]>(MOCK_ENTRIES);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<"issue" | "repair" | "note">("issue");

  const addEntry = () => {
    if (!title.trim()) return;
    const entry: DiaryEntry = {
      id: Date.now().toString(),
      date: new Date().toISOString().split("T")[0],
      title,
      description,
      images: [],
      category,
    };
    setEntries([entry, ...entries]);
    setTitle("");
    setDescription("");
    setShowForm(false);
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Байрны дневник</h1>
          <p className="text-sm text-slate-500 mt-0.5">Байрны доголдол, засварыг бүртгэн нотолгоо болго</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary text-sm">
          + Нэмэх
        </button>
      </div>

      {/* Info banner */}
      <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 mb-5 text-xs text-blue-800">
        💡 Байрны эзэнтэй маргаан гарсан тохиолдолд дневник нь хамгийн хүчтэй нотолгоо болно. Зураг болон огноотой тэмдэглэлийг хадгалаарай.
      </div>

      {/* New entry form */}
      {showForm && (
        <div className="card p-5 mb-5 border-blue-200 bg-blue-50">
          <h3 className="font-semibold text-slate-800 mb-4">Шинэ бичлэг</h3>
          <div className="space-y-3">
            <div>
              <label className="label">Төрөл</label>
              <div className="flex gap-2">
                {(["issue", "repair", "note"] as const).map((c) => (
                  <button
                    key={c}
                    onClick={() => setCategory(c)}
                    className={`text-xs px-3 py-1.5 rounded-full font-medium border transition-colors ${
                      category === c ? CATEGORY_LABELS[c].color + " border-current" : "border-slate-200 text-slate-500"
                    }`}
                  >
                    {CATEGORY_LABELS[c].label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="label">Гарчиг</label>
              <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Жишээ: Ус гоожиж байна" />
            </div>
            <div>
              <label className="label">Дэлгэрэнгүй тайлбар</label>
              <textarea className="input h-20 resize-none" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Болсон зүйлийг тайлбарлана уу..." />
            </div>
            <div>
              <label className="label">Зураг нэмэх</label>
              <div className="border-2 border-dashed border-slate-200 rounded-lg p-6 text-center text-sm text-slate-400 cursor-pointer hover:border-blue-300 transition-colors">
                📷 Зураг оруулах
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowForm(false)} className="btn-secondary text-sm">Болих</button>
              <button onClick={addEntry} className="btn-primary text-sm" disabled={!title.trim()}>Хадгалах</button>
            </div>
          </div>
        </div>
      )}

      {/* Entries */}
      {entries.length === 0 ? (
        <div className="card p-16 text-center text-slate-400">
          <div className="text-4xl mb-3">📔</div>
          <p className="text-sm">Дневник хоосон байна. Эхний бичлэг нэмнэ үү.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => {
            const cat = CATEGORY_LABELS[entry.category];
            return (
              <div key={entry.id} className="card p-4">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <h3 className="font-medium text-slate-900 text-sm">{entry.title}</h3>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cat.color}`}>{cat.label}</span>
                    <span className="text-xs text-slate-400">{entry.date}</span>
                  </div>
                </div>
                {entry.description && (
                  <p className="text-sm text-slate-600">{entry.description}</p>
                )}
                {entry.images.length > 0 && (
                  <div className="flex gap-2 mt-3">
                    {entry.images.map((img, i) => (
                      <div key={i} className="w-16 h-16 rounded-lg bg-slate-100" />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
