"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import LeaseTimeline from "@/components/LeaseTimeline";
import { getContracts, isAuthenticated } from "@/lib/api";
import type { Contract } from "@/lib/api";

export default function ContractTrackerPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [needsLogin, setNeedsLogin] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isAuthenticated()) {
      setNeedsLogin(true);
      setLoading(false);
      return;
    }
    getContracts()
      .then(setContracts)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const getDaysLeft = (endDate: string) => {
    return Math.ceil((new Date(endDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  };

  if (loading) return <div className="max-w-3xl mx-auto px-4 py-12 text-center text-slate-400 text-sm">Уншиж байна...</div>;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Гэрээний хяналт</h1>
          <p className="text-sm text-slate-500 mt-0.5">Түрээсийн гэрээний хугацаа болон сануулга</p>
        </div>
        <Link href="/contracts/generate" className="btn-primary text-sm">
          + Шинэ гэрээ
        </Link>
      </div>

      {needsLogin ? (
        <div className="card p-16 text-center text-slate-500">
          <div className="text-4xl mb-3">🔐</div>
          <p className="text-sm">Гэрээнүүдээ харахын тулд нэвтэрнэ үү.</p>
          <Link href="/login" className="text-blue-600 text-sm mt-2 inline-block hover:underline">
            Нэвтрэх →
          </Link>
        </div>
      ) : error ? (
        <div className="card p-6 text-center text-sm text-red-700 bg-red-50 border-red-200">{error}</div>
      ) : contracts.length === 0 ? (
        <div className="card p-16 text-center text-slate-400">
          <div className="text-4xl mb-3">📄</div>
          <p className="text-sm">Гэрээ байхгүй байна.</p>
          <Link href="/contracts/generate" className="text-blue-600 text-sm mt-2 inline-block hover:underline">
            Шинэ гэрээ үүсгэх →
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {contracts.map((c) => {
            const daysLeft = getDaysLeft(c.endDate);
            const isUrgent = daysLeft <= 30;
            const isExpired = daysLeft < 0;

            return (
              <div key={c.id} className={`card p-5 ${isUrgent && !isExpired ? "border-amber-300" : ""} ${isExpired ? "border-red-300 opacity-70" : ""}`}>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <h3 className="font-semibold text-slate-900">{c.address}</h3>
                    <p className="text-sm text-slate-500 mt-0.5">
                      {c.tenantName} · {Number(c.monthlyRent).toLocaleString()} ₮/сар
                    </p>
                  </div>
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full whitespace-nowrap ${
                    isExpired ? "bg-slate-100 text-slate-500" :
                    isUrgent ? "bg-amber-100 text-amber-700" : "bg-green-100 text-green-700"
                  }`}>
                    {isExpired ? "Дууссан" : isUrgent ? `⚠️ ${daysLeft} хоног үлдсэн` : `${daysLeft} хоног`}
                  </span>
                </div>

                <LeaseTimeline startDate={c.startDate} endDate={c.endDate} />

                <div className="flex gap-2 mt-4">
                  <Link href={`/contracts/sign/${c.id}`} className="btn-secondary text-xs py-1.5 flex-1 text-center">
                    Дэлгэрэнгүй
                  </Link>
                  <a href={`/api/contracts/${c.id}/pdf`} target="_blank" className="btn-secondary text-xs py-1.5 flex-1 text-center">
                    PDF татах
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
