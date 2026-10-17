"use client";

import { useEffect, useState } from "react";
import { getPendingAds, approveAd, rejectAd, Ad } from "@/lib/api";

export default function AdminPendingPage() {
  const [ads, setAds] = useState<Ad[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewComment, setReviewComment] = useState("");
  const [selectedAd, setSelectedAd] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getPendingAds();
        setAds(data);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await getPendingAds();
      setAds(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string) => {
    if (!window.confirm("Та энэ зарын зөвшөөрөл өгөхөд итгэлтэй байна уу?")) return;
    await approveAd(id, { admin_comment: reviewComment });
    await refresh();
    setReviewComment("");
    setSelectedAd(null);
  };

  const handleReject = async (id: string) => {
    if (!window.confirm("Та энэ зарын зөвшөөрөл өгөхгүй гэж татгалзах уу?")) return;
    await rejectAd(id, { admin_comment: reviewComment });
    await refresh();
    setReviewComment("");
    setSelectedAd(null);
  };

  return (
    <main className="page-shell py-10">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Админ: Хүлээгдэж буй зар</h1>
          <p className="text-sm text-slate-500">Зар оруулсны дараа админ баталгаажуулна. Та зөвшөөрөх эсэхийг сонгоно.</p>
        </div>
        <button onClick={refresh} className="btn-secondary">
          Шинэчлэх
        </button>
      </div>

      {loading && <div className="card p-6 text-slate-500">Үйлдэл хийгдэж байна...</div>}
      {error && <div className="card p-6 text-red-600">{error}</div>}
      {!loading && !error && ads.length === 0 && <div className="card p-6 text-slate-500">Хүлээгдэж буй зар байхгүй байна.</div>}

      <div className="space-y-4">
        {ads.map((ad) => (
          <div key={ad.id} className="card p-5 border-slate-200">
            <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">{ad.title}</h2>
                <p className="text-sm text-slate-500 mt-1">{ad.address}</p>
                <div className="mt-3 text-sm text-slate-600">{ad.description}</div>
              </div>
              <div className="text-right text-sm text-slate-500 min-w-[180px]">
                <div>Үнэ: {(ad.price / 1_000_000).toFixed(1)}M ₮</div>
                <div>Талбай: {ad.area} м²</div>
                <div>Өрөө: {ad.rooms}</div>
                <div>Огноо: {new Date(ad.createdAt).toLocaleDateString("mn-MN")}</div>
              </div>
            </div>

            <div className="mt-5">
              <label className="text-sm font-medium text-slate-700">Админ тайлбар</label>
              <textarea
                value={selectedAd === ad.id ? reviewComment : ""}
                onChange={(e) => {
                  setSelectedAd(ad.id);
                  setReviewComment(e.target.value);
                }}
                className="input mt-2 min-h-[120px] w-full resize-none"
                placeholder="Зар хүлээн зөвшөөрөх эсэх тайлбар оруулна.
" 
              />
            </div>

            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => handleApprove(ad.id)}
                className="btn-primary"
              >
                Зөвшөөрөх
              </button>
              <button
                type="button"
                onClick={() => handleReject(ad.id)}
                className="btn-secondary"
              >
                Татгалзах
              </button>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
