"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getAdminStats } from "@/lib/api";

export default function AdminPage() {
  const [stats, setStats] = useState({
    pendingCount: 0,
    approvedCount: 0,
    rejectedCount: 0,
    totalAds: 0,
    totalUsers: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getAdminStats();
        setStats(data);
      } catch (err) {
        setError((err as Error).message || "Админ мэдээлэл авах боломжгүй байна");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  return (
    <main className="page-shell py-10">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Админ самбар</h1>
          <p className="text-sm text-slate-500">Зар, хэрэглэгчийн үйл ажиллагааг удирдах.</p>
        </div>
        <Link href="/admin/pending" className="btn-primary">
          Хүлээгдэж буй зарууд
        </Link>
      </div>

      {loading && <div className="card p-6 text-slate-500">Түр хүлээнэ үү...</div>}
      {error && <div className="card p-6 text-red-600">{error}</div>}

      {!loading && !error && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="card p-5">
            <p className="text-sm text-slate-500">Хүлээгдэж буй зар</p>
            <p className="mt-2 text-3xl font-bold text-amber-600">{stats.pendingCount}</p>
          </div>
          <div className="card p-5">
            <p className="text-sm text-slate-500">Зөвшөөрөгдсөн зар</p>
            <p className="mt-2 text-3xl font-bold text-emerald-600">{stats.approvedCount}</p>
          </div>
          <div className="card p-5">
            <p className="text-sm text-slate-500">Татгалзсан зар</p>
            <p className="mt-2 text-3xl font-bold text-rose-600">{stats.rejectedCount}</p>
          </div>
          <div className="card p-5">
            <p className="text-sm text-slate-500">Нийт хэрэглэгч</p>
            <p className="mt-2 text-3xl font-bold text-blue-600">{stats.totalUsers}</p>
          </div>
        </div>
      )}
    </main>
  );
}
