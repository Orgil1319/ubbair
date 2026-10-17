"use client";

import { useState, useEffect } from "react";
import { getPriceAnalysis } from "@/lib/api";
import type { PriceAnalysis as PriceAnalysisType } from "@/lib/api";

interface Props {
  propertyId: string;
  price: number;
  area: number;
  district: string;
}

export default function PriceAnalysis({ propertyId, price, area, district }: Props) {
  const [data, setData] = useState<PriceAnalysisType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPriceAnalysis(propertyId).then(setData).finally(() => setLoading(false));
  }, [propertyId]);

  const pricePerM2 = price / area;
  const avgPerM2 = data?.districtAvgPerM2 ?? 0;
  const diff = avgPerM2 ? ((pricePerM2 - avgPerM2) / avgPerM2) * 100 : null;

  if (loading) return <div className="card p-8 text-center text-slate-400 text-sm">Үнийн дата татаж байна...</div>;

  return (
    <div className="space-y-3">
      {/* Summary card */}
      <div className="card p-5">
        <h2 className="section-title mb-4">Үнийн шинжилгээ</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-slate-500 mb-1">Энэ байрны м² үнэ</div>
            <div className="text-xl font-bold text-slate-900">{(pricePerM2 / 1_000_000).toFixed(2)}M ₮</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">{district}-ийн дундаж</div>
            <div className="text-xl font-bold text-slate-500">{(avgPerM2 / 1_000_000).toFixed(2)}M ₮</div>
          </div>
        </div>

        {diff !== null && (
          <div className={`mt-4 p-3 rounded-lg text-sm font-medium ${
            Math.abs(diff) < 10 ? "bg-green-50 text-green-800" :
            diff > 0 ? "bg-red-50 text-red-800" : "bg-blue-50 text-blue-800"
          }`}>
            {Math.abs(diff) < 10
              ? `✅ Үнэ орчин тойрны дундаждаа ойрхон байна (${diff > 0 ? "+" : ""}${diff.toFixed(0)}%)`
              : diff > 0
              ? `⚠️ Үнэ дүүргийн дундажаас ${diff.toFixed(0)}% өндөр байна. Хэт үнэлэгдсэн байж болзошгүй.`
              : `ℹ️ Үнэ дүүргийн дундажаас ${Math.abs(diff).toFixed(0)}% бага байна.`}
          </div>
        )}
      </div>

      {/* Comparable properties */}
      {data?.comparables && data.comparables.length > 0 && (
        <div className="card p-4">
          <h3 className="text-sm font-semibold text-slate-800 mb-3">Ойролцоо байрнуудтай харьцуулалт</h3>
          <div className="space-y-2">
            {data.comparables.map((c, i) => (
              <div key={i} className="flex items-center justify-between text-sm py-2 border-b border-slate-50 last:border-0">
                <div>
                  <div className="text-slate-700 font-medium">{c.title}</div>
                  <div className="text-xs text-slate-400">{c.area}м² · {c.district}</div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-slate-900">{(c.price / 1_000_000).toFixed(0)}M ₮</div>
                  <div className="text-xs text-slate-400">{(c.price / c.area / 1_000_000).toFixed(2)}M/м²</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Historical trend placeholder */}
      <div className="card p-4">
        <h3 className="text-sm font-semibold text-slate-800 mb-2">Үнийн өөрчлөлт (сүүлийн 12 сар)</h3>
        <div className="h-20 bg-slate-50 rounded-lg flex items-center justify-center text-xs text-slate-400">
          Recharts chart энд байрлана
        </div>
      </div>

      <p className="text-xs text-slate-400 text-center">Дата: unegui.mn · Нийслэлийн кадастр · {data?.updatedAt}</p>
    </div>
  );
}
