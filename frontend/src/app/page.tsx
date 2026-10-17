"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import RiskBadge from "@/components/RiskBadge";
import DataFreshnessTag from "@/components/DataFreshnessTag";
import { listPublicAds, getImageUrl, type Ad } from "@/lib/api";

const FEATURED = [
  {
    id: "1",
    title: "Сүхбаатар дүүрэг, 2 өрөө",
    price: 145_000_000,
    area: 52,
    district: "Сүхбаатар",
    risk: "low" as const,
    image: "/images/apt1.jpg",
    updatedAt: "2025-05-10",
  },
  {
    id: "2",
    title: "Чингэлтэй дүүрэг, 3 өрөө",
    price: 210_000_000,
    area: 78,
    district: "Чингэлтэй",
    risk: "medium" as const,
    image: "/images/apt2.jpg",
    updatedAt: "2025-05-08",
  },
  {
    id: "3",
    title: "Баянзүрх дүүрэг, 1 өрөө",
    price: 89_000_000,
    area: 38,
    district: "Баянзүрх",
    risk: "high" as const,
    image: "/images/apt3.jpg",
    updatedAt: "2025-05-10",
  },
];

export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [ads, setAds] = useState<Ad[]>([]);

  useEffect(() => {
    const loadAds = async () => {
      try {
        const data = await listPublicAds();
        setAds(data);
      } catch {
        setAds([]);
      }
    };

    loadAds();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query)}`);
    }
  };

  return (
    <main className="app-shell relative overflow-hidden">
      {/* Absolute Background Orbs for Premium Glassmorphism Feel */}
      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-blue-400 rounded-full mix-blend-multiply filter blur-[128px] opacity-40 animate-float" />
      <div className="absolute top-[20%] right-[-10%] w-[500px] h-[500px] bg-indigo-400 rounded-full mix-blend-multiply filter blur-[128px] opacity-40 animate-float-delayed" />
      
      {/* Nav */}
      <nav className="absolute top-0 w-full z-50">
        <div className="page-shell h-20 flex items-center justify-between">
          <Link href="/" className="font-extrabold text-2xl tracking-tighter text-slate-900 flex items-center gap-2">
            <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white text-lg">🏠</span>
            УБ Байр
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
            <Link href="/search" className="hover:text-blue-600 transition-colors">Хайх</Link>
            <Link href="/ads" className="hover:text-blue-600 transition-colors">Миний зар</Link>
            <Link href="/lease" className="hover:text-blue-600 transition-colors">Түрээс</Link>
            <Link href="/blacklist" className="hover:text-blue-600 transition-colors">Хар жагсаалт</Link>
            <Link href="/login" className="hover:text-blue-600 transition-colors">Нэвтрэх</Link>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/register" className="text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors">
              Бүртгүүлэх
            </Link>
            <Link href="/contracts/generate" className="btn-primary text-sm hidden sm:block">
              Гэрээ үүсгэх
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 pt-32 pb-20 px-6 min-h-[85vh] flex flex-col justify-center items-center text-center">
        <div className="max-w-4xl mx-auto">
          <div className="eyebrow mb-8">
            <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
            AI-д суурилсан үл хөдлөхийн зөвлөгч
          </div>
          
          <h1 className="text-5xl md:text-7xl font-extrabold text-slate-900 mb-8 leading-[1.08] tracking-tight">
            Байр авахаасаа өмнө <br className="hidden md:block" />
            <span className="text-gradient bg-clip-text text-transparent bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600">эрсдэлийг нь тооц.</span>
          </h1>
          
          <p className="text-lg text-slate-600 mb-12 max-w-2xl mx-auto leading-relaxed font-medium">
            Үерийн бүс, барилгын зөвшөөрөл, компаниудын хар жагсаалт болон зах зээлийн үнийн хөөсийг ганц хайлтаар шалгаж, эрсдэлгүй шийдвэр гаргаарай.
          </p>

          <div className="glass-panel p-2 max-w-2xl mx-auto">
            <form onSubmit={handleSearch} className="flex gap-2 relative">
              <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Хаяг, дүүрэг, барилгын нэрээр хайх..."
                className="flex-1 bg-transparent pl-12 pr-4 py-4 text-slate-900 text-base focus:outline-none placeholder:text-slate-400"
              />
              <button type="submit" className="btn-primary px-8 whitespace-nowrap text-base shadow-lg shadow-blue-600/20">
                Хайх
              </button>
            </form>
          </div>
          
          <div className="flex flex-wrap justify-center gap-6 mt-10 text-sm font-medium text-slate-500">
            <span className="flex items-center gap-2"><span className="text-green-500">✓</span> Үнэ + эрсдэл + түүх нэг дор</span>
            <span className="flex items-center gap-2"><span className="text-green-500">✓</span> Түрээслэгчийн эрх хамгаалалт</span>
            <span className="flex items-center gap-2"><span className="text-green-500">✓</span> AI зөвлөгчтэй шууд асуулт</span>
          </div>
        </div>
      </section>

      {/* Floating Stats */}
      <section className="relative z-20 page-shell -mt-10 mb-24">
        <div className="surface-card p-8 grid grid-cols-2 md:grid-cols-4 gap-8 divide-x divide-slate-200/50">
          <div className="text-center px-4">
            <div className="text-4xl font-extrabold text-slate-900 mb-1">2.4k+</div>
            <div className="text-sm font-medium text-slate-500 uppercase tracking-wider">Шалгасан байр</div>
          </div>
          <div className="text-center px-4">
            <div className="text-4xl font-extrabold text-blue-600 mb-1">340</div>
            <div className="text-sm font-medium text-slate-500 uppercase tracking-wider">Хар жагсаалтад</div>
          </div>
          <div className="text-center px-4">
            <div className="text-4xl font-extrabold text-red-500 mb-1">18</div>
            <div className="text-sm font-medium text-slate-500 uppercase tracking-wider">Үерийн эрсдэл</div>
          </div>
          <div className="text-center px-4">
            <div className="text-4xl font-extrabold text-amber-500 mb-1">800+</div>
            <div className="text-sm font-medium text-slate-500 uppercase tracking-wider">Зөвшөөрөлгүй</div>
          </div>
        </div>
      </section>

      {/* Public Ads */}
      {ads.length > 0 && (
        <section className="relative z-10 page-shell py-16">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-4">
            <div>
              <h2 className="text-3xl font-extrabold text-slate-900 mb-3 tracking-tight">Шинэ зарууд</h2>
              <p className="text-slate-500">Админ зөвшөөрөгдсөн зарууд энд гарч байна.</p>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {ads.map((ad) => (
              <Link key={ad.id} href={`/property/${ad.id}`} className="card overflow-hidden bg-white/70 block hover:shadow-lg transition-shadow">
                {ad.photoUrl ? (
                  <img src={getImageUrl(ad.photoUrl) ?? undefined} alt={ad.title} className="h-56 w-full object-cover" />
                ) : (
                  <div className="h-56 bg-slate-200" />
                )}
                <div className="p-6">
                  <h3 className="text-lg font-bold text-slate-900 mb-2">{ad.title}</h3>
                  <p className="text-sm text-slate-500 mb-3">{ad.address}</p>
                  <div className="flex items-center gap-3 text-sm text-slate-600">
                    <span className="font-semibold text-slate-900">{(ad.price / 1_000_000).toFixed(0)}M ₮</span>
                    <span>{ad.area} м²</span>
                    <span>{ad.rooms} өрөө</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Featured Properties */}
      <section className="relative z-10 page-shell py-16">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-4">
          <div>
            <h2 className="text-3xl font-extrabold text-slate-900 mb-3 tracking-tight">Онцлох байрууд</h2>
            <p className="text-slate-500">Зах зээлд шинээр нэмэгдсэн байрнуудын эрсдэлийн мэдээлэл.</p>
          </div>
          <DataFreshnessTag date="2025-05-10" />
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {FEATURED.map((p) => (
            <Link key={p.id} href={`/property/${p.id}`} className="card group overflow-hidden bg-white/70">
              <div className="bg-slate-200 h-56 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-slate-900/20 to-transparent z-10" />
                {/* Fallback pattern if image is missing */}
                <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10" />
                
                <div className="absolute top-4 right-4 z-20">
                  <RiskBadge level={p.risk} />
                </div>
                
                <div className="absolute bottom-4 left-4 z-20">
                  <div className="text-white font-bold text-2xl drop-shadow-md">
                    {(p.price / 1_000_000).toFixed(0)} сая ₮
                  </div>
                </div>
              </div>
              <div className="p-6">
                <h3 className="text-lg font-bold text-slate-900 group-hover:text-blue-600 transition-colors line-clamp-1 mb-2">
                  {p.title}
                </h3>
                <div className="flex items-center gap-4 text-sm text-slate-500 font-medium">
                  <span className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"></path></svg>
                    {p.area} м²
                  </span>
                  <span className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.242-4.243a8 8 0 1111.314 0z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                    {p.district}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 page-shell py-20">
        <div className="grid md:grid-cols-2 gap-8">
          <div className="card p-8 bg-gradient-to-br from-amber-50 to-orange-50 border-amber-100 relative overflow-hidden group">
            <div className="absolute right-0 top-0 w-32 h-32 bg-amber-200/40 rounded-full blur-2xl -mr-10 -mt-10 transition-transform group-hover:scale-150 duration-500" />
            <div className="relative z-10">
              <div className="w-12 h-12 bg-amber-100 rounded-2xl flex items-center justify-center text-2xl mb-6 shadow-sm border border-amber-200">⚠️</div>
              <h3 className="text-xl font-bold text-slate-900 mb-3 tracking-tight">Хар жагсаалт шалгах</h3>
              <p className="text-slate-600 mb-8 leading-relaxed">
                Компанийн нэр эсвэл регистрийн дугаараар хайж НХБХГ болон Мэргэжлийн хяналтын хар жагсаалтад орсон эсэхийг баталгаатай шалгана уу.
              </p>
              <Link href="/blacklist" className="inline-flex items-center gap-2 text-sm font-bold text-amber-700 bg-amber-100/50 px-5 py-2.5 rounded-xl hover:bg-amber-100 transition-colors">
                Шалгах <span className="text-lg leading-none">→</span>
              </Link>
            </div>
          </div>
          
          <div className="card p-8 bg-gradient-to-br from-emerald-50 to-teal-50 border-emerald-100 relative overflow-hidden group">
            <div className="absolute right-0 top-0 w-32 h-32 bg-emerald-200/40 rounded-full blur-2xl -mr-10 -mt-10 transition-transform group-hover:scale-150 duration-500" />
            <div className="relative z-10">
              <div className="w-12 h-12 bg-emerald-100 rounded-2xl flex items-center justify-center text-2xl mb-6 shadow-sm border border-emerald-200">📄</div>
              <h3 className="text-xl font-bold text-slate-900 mb-3 tracking-tight">Стандарт гэрээ үүсгэх</h3>
              <p className="text-slate-600 mb-8 leading-relaxed">
                Иргэний хуулийн 318-р зүйлд нийцсэн, хоёр талын эрх ашгийг бүрэн хамгаалсан хууль зүйн баталгаат гэрээний загвар үүсгэх.
              </p>
              <Link href="/contracts/generate" className="inline-flex items-center gap-2 text-sm font-bold text-emerald-700 bg-emerald-100/50 px-5 py-2.5 rounded-xl hover:bg-emerald-100 transition-colors">
                Үүсгэх <span className="text-lg leading-none">→</span>
              </Link>
            </div>
          </div>
        </div>
      </section>
      
      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white/50 py-10 mt-10">
        <div className="page-shell text-center text-slate-500 text-sm font-medium">
          <p>© 2026 УБ Байр Систем. Хуулийн зөвлөгөө өгөх AI платформ.</p>
        </div>
      </footer>
    </main>
  );
}
