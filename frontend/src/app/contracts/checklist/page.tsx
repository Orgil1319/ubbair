"use client";

import { useState } from "react";

interface CheckItem {
  id: string;
  label: string;
  description: string;
  law?: string;
  required: boolean;
}

const CHECKLIST: CheckItem[] = [
  {
    id: "written",
    label: "Гэрээ бичгээр байгуулагдсан уу?",
    description: "Амаар хийсэн гэрээ хуулийн хүчин чадлаа алдаж болзошгүй. Бүх нөхцөлийг бичгээр тогтоох шаардлагатай.",
    law: "ИХ 318-р зүйл",
    required: true,
  },
  {
    id: "registered",
    label: "Гэрээг Үл хөдлөх хөрөнгийн газарт бүртгүүлэх үү?",
    description: "Бүртгэлгүй гэрээ хуулийн хүчин чадалгүй болно. Гэрээнд гарын үсэг зурсаны дараа 7 хоногт бүртгүүлнэ.",
    law: "ИХ 318.4",
    required: true,
  },
  {
    id: "deposit",
    label: "Барьцаа мөнгийг буцааж өгөх нөхцөл гэрээнд байгаа уу?",
    description: "Барьцаа мөнгийг хэзээ, ямар нөхцөлд буцааж өгөхийг гэрээнд тодорхой заасан байх хэрэгтэй.",
    required: true,
  },
  {
    id: "notice",
    label: "Урьдчилан мэдэгдэх хоногийг тогтоосон уу?",
    description: "Байрны эзэн болон түрээслэгч аль нэг нь гэрээ цуцлах тохиолдолд нөгөө талдаа хэдэн хоногийн өмнө мэдэгдэхийг заах шаардлагатай.",
    law: "ИХ 204-р зүйл",
    required: true,
  },
  {
    id: "utility",
    label: "Нийтийн үйлчилгээний төлбөр (цахилгаан, ус, халаалт) хэн төлөхийг заасан уу?",
    description: "Нийтийн үйлчилгээний төлбөрийг хэн хариуцахыг гэрээнд тодорхой бичнэ.",
    required: false,
  },
  {
    id: "repair",
    label: "Их засвар, жижиг засварыг хэн хариуцахыг заасан уу?",
    description: "Барилгын том засварыг байрны эзэн, өдөр тутмын жижиг засварыг түрээслэгч хариуцах нь нийтлэг стандарт.",
    required: false,
  },
  {
    id: "sublease",
    label: "Дахин түрээслэх боломжийг зааж өгсөн үү?",
    description: "Оюутнуудын хувьд ихэвчлэн хамрагчийг нэмэх эсэхийг байрны эзнээс зөвшөөрөл авахыг гэрээнд заана.",
    required: false,
  },
  {
    id: "inventory",
    label: "Байрны тавилга, тоног төхөөрөмжийн жагсаалт үйлдсэн үү?",
    description: "Гэрээ дуусгавар болоход маргаан гарахаас сэргийлж байрны бүх зүйлийг дурьдсан хавсралт бэлтгэнэ.",
    required: false,
  },
];

export default function ChecklistPage() {
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  const toggle = (id: string) => setChecked((c) => ({ ...c, [id]: !c[id] }));

  const requiredCount = CHECKLIST.filter((i) => i.required).length;
  const checkedRequired = CHECKLIST.filter((i) => i.required && checked[i.id]).length;
  const allRequiredDone = checkedRequired === requiredCount;

  return (
    <div className="page-shell max-w-3xl">
      <div className="mb-6">
        <h1 className="page-title mb-2">5 минутын хуулийн чек-лист</h1>
        <p className="page-copy">Гэрээ байгуулахаасаа өмнө эдгээр зүйлийг шалгана уу.</p>
      </div>

      {/* Progress */}
      <div className="card p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-slate-700">Заавал шаардлагатай зүйлс</span>
          <span className="text-sm font-bold text-slate-900">{checkedRequired}/{requiredCount}</span>
        </div>
        <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${allRequiredDone ? "bg-green-500" : "bg-blue-500"}`}
            style={{ width: `${(checkedRequired / requiredCount) * 100}%` }}
          />
        </div>
        {allRequiredDone && (
          <p className="text-xs text-green-700 mt-2 font-medium">✅ Заавал шаардлагатай бүх зүйлийг шалгасан байна!</p>
        )}
      </div>

      {/* Required items */}
      <div className="mb-4">
        <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-3">Заавал шаардлагатай</h2>
        <div className="space-y-2">
          {CHECKLIST.filter((i) => i.required).map((item) => (
            <ChecklistItem key={item.id} item={item} checked={!!checked[item.id]} onToggle={() => toggle(item.id)} />
          ))}
        </div>
      </div>

      {/* Optional items */}
      <div>
        <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-3">Нэмэлт зөвлөмж</h2>
        <div className="space-y-2">
          {CHECKLIST.filter((i) => !i.required).map((item) => (
            <ChecklistItem key={item.id} item={item} checked={!!checked[item.id]} onToggle={() => toggle(item.id)} />
          ))}
        </div>
      </div>

      {allRequiredDone && (
        <div className="mt-6 card p-4 bg-green-50 border-green-200 text-center">
          <p className="text-sm font-medium text-green-800 mb-2">Бүх шаардлагатай зүйлийг шалгасан байна!</p>
          <a href="/contracts/generate" className="btn-primary text-sm">
            Гэрээ үүсгэх →
          </a>
        </div>
      )}
    </div>
  );
}

function ChecklistItem({ item, checked, onToggle }: { item: CheckItem; checked: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className={`w-full text-left card p-4 transition-all hover:shadow-md ${checked ? "border-green-300 bg-green-50" : ""}`}
    >
      <div className="flex items-start gap-3">
        <div className={`w-5 h-5 rounded border-2 shrink-0 mt-0.5 flex items-center justify-center transition-colors ${
          checked ? "bg-green-500 border-green-500" : "border-slate-300"
        }`}>
          {checked && <span className="text-white text-xs font-bold">✓</span>}
        </div>
        <div className="flex-1">
          <div className={`text-sm font-medium ${checked ? "text-green-800 line-through decoration-green-400" : "text-slate-800"}`}>
            {item.label}
          </div>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">{item.description}</p>
          {item.law && (
            <span className="inline-block mt-1.5 text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
              {item.law}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}
