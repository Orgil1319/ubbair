"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import RiskBadge from "@/components/RiskBadge";
import AiAdvisor from "@/components/AiAdvisor";
import PriceAnalysis from "@/components/PriceAnalysis";
import DataFreshnessTag from "@/components/DataFreshnessTag";
import { getProperty, getRiskAssessment, getImageUrl, listPublicAds } from "@/lib/api";
import type { Property, RiskAssessment, Ad } from "@/lib/api";
import dynamic from "next/dynamic";

const MapView = dynamic(() => import("@/components/MapView"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-slate-100 rounded-xl flex items-center justify-center animate-pulse">
      <span className="text-sm text-slate-400">Газрын зураг уншиж байна...</span>
    </div>
  ),
});

export default function PropertyDetailPage() {
  const params = useParams();
  const id = typeof params?.id === "string" ? params.id : Array.isArray(params?.id) ? params.id[0] : "";
  const [property, setProperty] = useState<Property | null>(null);
  const [ad, setAd] = useState<Ad | null>(null);
  const [risk, setRisk] = useState<RiskAssessment | null>(null);
  const [tab, setTab] = useState<"overview" | "risk" | "price" | "advisor">("overview");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;

    const load = async () => {
      try {
        const ads = await listPublicAds();
        const publicAd = ads.find((item) => item.id === id) ?? null;
        setAd(publicAd);

        if (publicAd) {
          setProperty(null);
          setRisk(null);
          setLoading(false);
          return;
        }

        const [propertyResult, riskResult] = await Promise.allSettled([getProperty(id), getRiskAssessment(id)]);
        if (propertyResult.status === "fulfilled") {
          setProperty(propertyResult.value);
        }
        if (riskResult.status === "fulfilled") {
          setRisk(riskResult.value);
        }
      } catch (err) {
        console.error("Failed to load property data:", err);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center text-slate-400">
        <div className="animate-spin text-4xl mb-3">⏳</div>
        <p className="text-sm">Мэдээлэл татаж байна...</p>
      </div>
    );
  }

  if (!property && !ad) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center text-slate-400">
        <p>Байр олдсонгүй.</p>
        <Link href="/search" className="text-blue-600 text-sm mt-2 inline-block">← Хайлт руу буцах</Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      {/* Back */}
      <Link href="/search" className="text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1 mb-4">
        ← Хайлт руу буцах
      </Link>

      {/* Map */}
      {(property || ad) && (
        <div className="rounded-xl h-64 mb-4 relative z-0">
          {property ? (
            <MapView 
              properties={[property]} 
              center={[property.lat, property.lng]} 
              zoom={14} 
            />
          ) : (
            <div className="w-full h-full rounded-xl bg-slate-100 flex items-center justify-center text-sm text-slate-500">
              Байршил мэдээлэлгүй зар
            </div>
          )}
          <div className="absolute top-3 right-3 z-[1000] pointer-events-none">
            <RiskBadge level={risk?.level ?? "low"} size="lg" />
          </div>
        </div>
      )}

      {/* Title */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{(property ?? ad)?.title}</h1>
          <p className="text-slate-500 text-sm mt-0.5">{(property ?? ad)?.address}</p>
        </div>
        <div className="text-right shrink-0">
          <div className="text-xl font-bold text-slate-900">{(((property ?? ad)?.price ?? 0) / 1_000_000).toFixed(0)}M ₮</div>
          <div className="text-xs text-slate-500">{(((property ?? ad)?.price ?? 0) / ((property ?? ad)?.area ?? 1) / 1_000_000).toFixed(1)}M/м²</div>
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        {[
          { label: "Талбай", value: `${(property ?? ad)?.area ?? 0} м²` },
          { label: "Өрөө", value: `${(property ?? ad)?.rooms ?? 0} өрөө` },
          { label: "Төрөл", value: property ? `${property.floor}/${property.totalFloors}` : ad?.propertyType ?? "Зар" },
        ].map((s) => (
          <div key={s.label} className="card p-3 text-center">
            <div className="font-semibold text-slate-900 text-sm">{s.value}</div>
            <div className="text-xs text-slate-500 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-slate-100 p-1 rounded-lg">
        {(["overview", "risk", "price", "advisor"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${
              tab === t ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {{ overview: "Дэлгэрэнгүй", risk: "🛡 Эрсдэл", price: "📊 Үнэ", advisor: "🤖 AI" }[t]}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "overview" && (
        <div className="card p-5 space-y-4">
          {ad?.photoUrl && (
            <img src={getImageUrl(ad.photoUrl) ?? undefined} alt={ad.title} className="h-64 w-full rounded-2xl object-cover" />
          )}
          {ad?.photoUrl && (
            <img src={getImageUrl(ad.photoUrl) ?? undefined} alt={ad.title} className="h-64 w-full rounded-2xl object-cover" />
          )}
          <div>
            <h2 className="section-title mb-2">{property ? "Байрны тухай" : "Зарын тухай"}</h2>
            <p className="text-sm text-slate-600">{property?.description ?? ad?.description}</p>
          </div>

          {ad && (
            <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4 space-y-2">
              <div className="text-sm font-semibold text-blue-900">🏠 Түрээслэх зорилготой зар</div>
              <p className="text-sm text-blue-800">Энэ зар нь түрээслэх зорилгоор оруулсан бөгөөд гэрээ, эрхийн талаар нэмэлт мэдээлэл авах боломжтой.</p>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-white px-2.5 py-1 text-blue-700">• Түрээсийн нөхцөл</span>
                <span className="rounded-full bg-white px-2.5 py-1 text-blue-700">• Барьцаа мөнгө</span>
                <span className="rounded-full bg-white px-2.5 py-1 text-blue-700">• Хууль зүйн хамгаалалт</span>
              </div>
            </div>
          )}
          <div className="grid grid-cols-2 gap-y-3 text-sm">
            {(property
              ? [
                  ["Барилгын жил", property.builtYear],
                  ["Дүүрэг", property.district],
                  ["Хороо", property.khoroo],
                  ["Барилгын төрөл", property.buildingType],
                  ["Барилгын компани", property.developer],
                  ["Барилгын зөвшөөрөл", property.permitStatus === "valid" ? "✅ Хүчинтэй" : "❌ Зөвшөөрөлгүй"],
                ]
              : [
                  ["Хаяг", ad?.address],
                  ["Үнэ", `${(ad?.price ?? 0).toLocaleString()}₮`],
                  ["Талбай", `${ad?.area ?? 0} м²`],
                  ["Өрөө", `${ad?.rooms ?? 0} өрөө`],
                  ["Төрөл", ad?.propertyType],
                  ["Статус", ad?.status === "approved" ? "Зөвшөөрөгдсөн" : "Хүлээгдэж буй"],
                ]
            ).map(([k, v]) => (
              <div key={String(k)}>
                <div className="text-slate-500 text-xs">{k}</div>
                <div className="font-medium text-slate-900">{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "risk" && risk && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="section-title">Эрсдэлийн тайлан</h2>
            <DataFreshnessTag date={risk.updatedAt} />
          </div>

          {/* Score */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-slate-600">Нийт эрсдэлийн оноо</span>
              <span className={`text-2xl font-bold ${
                risk.score < 30 ? "text-green-600" : risk.score < 60 ? "text-amber-600" : "text-red-600"
              }`}>
                {risk.score}/100
              </span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  risk.score < 30 ? "bg-green-500" : risk.score < 60 ? "bg-amber-500" : "bg-red-500"
                }`}
                style={{ width: `${risk.score}%` }}
              />
            </div>
          </div>

          {/* Risk items */}
          {risk.items?.map((item) => (
            <div key={item.type} className={`card p-4 border-l-4 ${
              item.severity === "critical" ? "border-red-500" :
              item.severity === "high" ? "border-orange-400" :
              item.severity === "medium" ? "border-amber-400" : "border-green-400"
            }`}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm text-slate-900">{item.label}</span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  item.severity === "critical" ? "bg-red-100 text-red-700" :
                  item.severity === "high" ? "bg-orange-100 text-orange-700" :
                  item.severity === "medium" ? "bg-amber-100 text-amber-700" : "bg-green-100 text-green-700"
                }`}>
                  {item.severity === "critical" ? "Маш өндөр" : item.severity === "high" ? "Өндөр" : item.severity === "medium" ? "Дунд" : "Аюулгүй"}
                </span>
              </div>
              <p className="text-xs text-slate-600 mb-2">{item.description}</p>
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100/50">
                <span className="text-[10px] text-slate-400 font-medium bg-slate-100/50 px-2 py-0.5 rounded">
                  Эх сурвалж: {item.source || "Тодорхойгүй"}
                </span>
                {item.updatedAt && (
                  <span className="text-[10px] text-slate-400 flex items-center gap-1">
                    🕒 {new Date(item.updatedAt).toLocaleDateString("mn-MN")}
                  </span>
                )}
              </div>
            </div>
          ))}

          <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 text-xs text-blue-800">
            ⚠️ Энэ тайлан нь зөвхөн мэдэгдэл бөгөөд баталгаа биш. Мэргэжлийн үнэлгээ авахыг зөвлөж байна.
          </div>
        </div>
      )}

      {tab === "price" && property && <PriceAnalysis propertyId={id} price={property.price} area={property.area} district={property.district} />}

      {tab === "advisor" && <AiAdvisor propertyId={id} propertyTitle={(property ?? ad)?.title ?? "Зар"} riskScore={risk?.score} />}

      {/* Action buttons */}
      <div className="flex gap-3 mt-6">
        <Link
          href={`/contracts/generate?propertyId=${id}&address=${encodeURIComponent((property ?? ad)?.address ?? "")}&rooms=${(property ?? ad)?.rooms ?? ""}&area=${(property ?? ad)?.area ?? ""}`}
          className="btn-primary flex-1 text-center text-sm"
        >
          📄 Түрээслэх гэрээ үүсгэх
        </Link>
        <button className="btn-secondary flex-1 text-sm">
          📞 Холбоо барих
        </button>
      </div>
    </div>
  );
}
