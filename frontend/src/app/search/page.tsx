"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import RiskBadge from "@/components/RiskBadge";
import { searchProperties, listPublicAds, getImageUrl, type Property, type Ad } from "@/lib/api";
import dynamic from "next/dynamic";

const MapView = dynamic(() => import("@/components/MapView"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-slate-100 rounded-xl flex items-center justify-center animate-pulse">
      <span className="text-sm text-slate-400">Газрын зураг уншиж байна...</span>
    </div>
  ),
});

const DISTRICTS = ["Бүгд", "Сүхбаатар", "Чингэлтэй", "Баянзүрх", "Баянгол", "Хан-Уул", "Сонгинохайрхан", "Налайх", "Багануур"];
const RISK_LEVELS = ["Бүгд", "Аюулгүй", "Дунд", "Өндөр"];

function SearchContent() {
  const params = useSearchParams();
  const [query, setQuery] = useState(params.get("q") ?? "");
  const [district, setDistrict] = useState("Бүгд");
  const [risk, setRisk] = useState("Бүгд");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [properties, setProperties] = useState<Property[]>([]);
  const [ads, setAds] = useState<Ad[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      try {
        const [propertyData, adData] = await Promise.all([
          searchProperties({
            q: query,
            district: district === "Бүгд" ? undefined : district,
            risk: risk === "Бүгд" ? undefined : risk,
            minPrice: minPrice ? Number(minPrice) * 1_000_000 : undefined,
            maxPrice: maxPrice ? Number(maxPrice) * 1_000_000 : undefined,
          }),
          listPublicAds(),
        ]);
        setProperties(propertyData);
        setAds(adData);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [query, district, risk, minPrice, maxPrice]);

  const results = [
    ...properties.map((p) => ({
      id: p.id,
      title: p.title,
      address: p.address,
      price: p.price,
      area: p.area,
      kind: "property" as const,
      imageUrl: null as string | null,
      riskLevel: p.riskLevel,
    })),
    ...ads.map((ad) => ({
      id: ad.id,
      title: ad.title,
      address: ad.address,
      price: ad.price,
      area: ad.area,
      kind: "ad" as const,
      imageUrl: ad.photoUrl ?? null,
      riskLevel: "low" as const,
    })),
  ];

  return (
    <div className="page-shell max-w-7xl py-6">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-xl font-bold text-slate-900">Байр хайх</h1>
        <p className="text-sm text-slate-500 mt-1">Үнэ, эрсдэл, компаниудын түүхийг нэг дор шалгана.</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Left Side: Search and List */}
        <div className="flex flex-col h-[calc(100vh-160px)]">
          {/* Search bar */}
          <div className="card p-4 mb-4 shrink-0">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Хаяг, дүүрэг, барилгын нэр..."
              className="input mb-3"
            />
            <div className="grid grid-cols-2 gap-3">
              {/* District */}
              <div>
                <label className="label">Дүүрэг</label>
                <select className="input text-xs" value={district} onChange={(e) => setDistrict(e.target.value)}>
                  {DISTRICTS.map((d) => <option key={d}>{d}</option>)}
                </select>
              </div>
              {/* Risk */}
              <div>
                <label className="label">Эрсдэл</label>
                <select className="input text-xs" value={risk} onChange={(e) => setRisk(e.target.value)}>
                  {RISK_LEVELS.map((r) => <option key={r}>{r}</option>)}
                </select>
              </div>
            </div>
          </div>

          {/* Result list */}
          <div className="flex-1 overflow-y-auto pr-2">
            <p className="text-sm text-slate-500 mb-3 sticky top-0 bg-slate-50 z-10 py-2">
              {loading ? "Хайж байна..." : `${results.length} үр дүн олдлоо`}
            </p>
            <div className="space-y-3 pb-6">
              {results.map((item) => (
                <Link key={item.id} href={`/property/${item.id}`} className="card p-4 flex gap-4 hover:shadow-md transition-shadow group block">
                  <div className="bg-slate-200 rounded-lg w-24 h-20 shrink-0 relative overflow-hidden">
                    {item.imageUrl ? (
                      <img src={getImageUrl(item.imageUrl) ?? undefined} alt={item.title} className="h-full w-full object-cover" />
                    ) : (
                      <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-medium text-slate-900 group-hover:text-blue-700 transition-colors text-sm truncate">
                        {item.title}
                      </h3>
                      {item.kind === "property" ? <RiskBadge level={item.riskLevel} /> : <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">Зар</span>}
                    </div>
                    <p className="text-slate-500 text-xs mt-0.5">{item.address}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-slate-600">
                      <span className="font-semibold text-slate-900">{(item.price / 1_000_000).toFixed(0)}M ₮</span>
                      <span>{item.area} м²</span>
                    </div>
                  </div>
                </Link>
              ))}
              {!loading && results.length === 0 && (
                <div className="text-center py-16 text-slate-400">
                  <div className="text-4xl mb-2">🔍</div>
                  <p className="text-sm">Байр олдсонгүй. Шүүлтүүрийг өөрчилнө үү.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Side: Map */}
        <div className="hidden lg:block h-[calc(100vh-160px)] sticky top-24 rounded-2xl overflow-hidden shadow-lg border border-slate-200 z-0">
          <MapView 
            properties={properties} 
            center={[47.92, 106.92]} // UB center
            zoom={12}
            showRiskLayer={true}
          />
        </div>
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense>
      <SearchContent />
    </Suspense>
  );
}
