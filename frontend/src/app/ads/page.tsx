"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listMyAds, Ad, getImageUrl } from "@/lib/api";

export default function MyAdsPage() {
  const [ads, setAds] = useState<Ad[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await listMyAds();
        setAds(data);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <main className="page-shell py-10">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Миний зар</h1>
          <p className="text-sm text-slate-500">Таны оруулсан зар, зөвшөөрөл болон статустай танилцана.</p>
        </div>
        <Link href="/ads/new" className="btn-primary w-full md:w-auto">
          Шинэ зар оруулах
        </Link>
      </div>

      {loading && (
        <div className="card p-6 text-slate-500">Татаж байна...</div>
      )}

      {error && (
        <div className="card p-6 text-red-600">{error}</div>
      )}

      {!loading && !error && ads.length === 0 && (
        <div className="card p-6 text-slate-500">Та одоогоор албан ёсны зар оруулсангүй.</div>
      )}

      <div className="space-y-4">
        {ads.map((ad) => (
          <div key={ad.id} className="card p-5 border-slate-200">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">{ad.title}</h2>
                <p className="text-sm text-slate-500 mt-1">{ad.address}</p>
              </div>
              <div className="text-right">
                <div className="text-sm text-slate-500">Үнэ: {(ad.price / 1_000_000).toFixed(1)}M ₮</div>
                <div className="text-sm text-slate-500">Мөр: {ad.rooms}, {ad.area} м²</div>
              </div>
            </div>

            {ad.photoUrl && (
              <div className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                <img
                  src={getImageUrl(ad.photoUrl) ?? undefined}
                  alt={ad.title}
                  className="h-56 w-full object-cover"
                />
              </div>
            )}

            <div className="mt-4 flex flex-wrap gap-2 items-center text-sm">
              <span className={`rounded-full px-3 py-1 font-medium text-white ${
                ad.status === "pending" ? "bg-amber-500" : ad.status === "approved" ? "bg-emerald-600" : "bg-red-600"
              }`}>
                {ad.status === "pending" ? "Хүлээгдэж буй" : ad.status === "approved" ? "Зөвшөөрөгдсөн" : "Татгалзсан"}
              </span>
              {ad.adminComment && <span className="text-slate-500">Ашгийн тайлбар: {ad.adminComment}</span>}
              <span className="text-slate-400">{new Date(ad.createdAt).toLocaleDateString("mn-MN")}</span>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
