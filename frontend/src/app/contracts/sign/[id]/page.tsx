"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { getContract, sendForSigning } from "@/lib/api";
import type { Contract } from "@/lib/api";

export default function ContractSignPage() {
  const { id } = useParams<{ id: string }>();
  const [contract, setContract] = useState<Contract | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    getContract(id).then(setContract).finally(() => setLoading(false));
  }, [id]);

  const handleSendForSign = async () => {
    if (!contract) return;
    setSending(true);
    await sendForSigning(id);
    setSent(true);
    setSending(false);
  };

  if (loading) return <div className="max-w-2xl mx-auto px-4 py-12 text-center text-slate-400 text-sm">Уншиж байна...</div>;
  if (!contract) return <div className="max-w-2xl mx-auto px-4 py-12 text-center text-slate-400 text-sm">Гэрээ олдсонгүй.</div>;

  if (sent) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <div className="text-5xl mb-4">📨</div>
        <h2 className="text-xl font-bold text-slate-900 mb-2">Гарын үсэг зурах хүсэлт илгээгдлээ</h2>
        <p className="text-slate-500 text-sm mb-6">
          {contract.ownerEmail} болон {contract.tenantEmail} хаягт и-мэйл илгээгдлээ.
          Талууд гарын үсэг зурсаны дараа гэрээ хүчинтэй болно.
        </p>
        <div className="card p-5 bg-amber-50 border-amber-200 text-left text-sm">
          <div className="font-semibold text-amber-900 mb-2">⚠️ Чухал дараагийн алхам</div>
          <p className="text-amber-800 mb-3">
            Цахим гарын үсэг зурсны дараа гэрээг <strong>Улсын бүртгэлийн ерөнхий газарт</strong> бүртгүүлэх шаардлагатай.
            Иргэний хуулийн 318.4-т заасны дагуу бүртгэлгүй гэрээ хүчин төгөлдөр бус болно.
          </p>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-amber-600">📍</span>
              <span className="text-amber-800">Улаанбаатар хот, Сүхбаатар дүүрэг, УБЕГ-ын байр</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-amber-600">📋</span>
              <span className="text-amber-800">Шаардлагатай баримт: гэрээний хуулбар, иргэний үнэмлэх, кадастрын гэрчилгээ</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-xl font-bold text-slate-900 mb-1">Гэрээг баталгаажуулах</h1>
      <p className="text-sm text-slate-500 mb-6">Гэрээний агуулгыг шалгаад, гарын үсэг зурах хүсэлт явуулна уу.</p>

      {/* Contract preview */}
      <div className="card p-5 mb-5">
        <div className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-4">Гэрээний хураангуй</div>
        <div className="grid grid-cols-2 gap-y-3 text-sm">
          {[
            ["Байрны эзэн", contract.ownerName],
            ["Түрээслэгч", contract.tenantName],
            ["Хаяг", contract.address],
            ["Талбай", `${contract.area} м²`],
            ["Сарын түрээс", `${Number(contract.monthlyRent).toLocaleString()} ₮`],
            ["Барьцаа мөнгө", `${Number(contract.deposit).toLocaleString()} ₮`],
            ["Эхлэх огноо", contract.startDate],
            ["Дуусах огноо", contract.endDate],
          ].map(([k, v]) => (
            <div key={k}>
              <div className="text-xs text-slate-400">{k}</div>
              <div className="font-medium text-slate-900">{v}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Signing status */}
      <div className="card p-4 mb-5">
        <div className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-3">Гарын үсгийн статус</div>
        <div className="space-y-3">
          {[
            { label: "Байрны эзэн", email: contract.ownerEmail, status: contract.ownerSigned ? "signed" : "pending" },
            { label: "Түрээслэгч", email: contract.tenantEmail, status: contract.tenantSigned ? "signed" : "pending" },
          ].map((p) => (
            <div key={p.label} className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-slate-800">{p.label}</div>
                <div className="text-xs text-slate-400">{p.email}</div>
              </div>
              <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                p.status === "signed"
                  ? "bg-green-100 text-green-700"
                  : "bg-slate-100 text-slate-500"
              }`}>
                {p.status === "signed" ? "✅ Гарын үсэг зурсан" : "⏳ Хүлээгдэж байна"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <a
          href={`/api/contracts/${id}/pdf`}
          target="_blank"
          className="btn-secondary flex-1 text-center text-sm"
        >
          📄 PDF харах
        </a>
        <button
          onClick={handleSendForSign}
          disabled={sending}
          className="btn-primary flex-1 text-sm"
        >
          {sending ? "Явуулж байна..." : "✉️ Гарын үсгийн хүсэлт явуулах"}
        </button>
      </div>
    </div>
  );
}
