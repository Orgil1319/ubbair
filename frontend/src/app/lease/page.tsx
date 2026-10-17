import Link from "next/link";

const RIGHTS = [
  {
    icon: "📝",
    title: "Гэрээний эрх",
    desc: "Гэрээ заавал бичгээр байх ёстой. Амаар хийсэн гэрээ маргаан гарсан үед хамгаалалт хангалтгүй.",
    law: "ИХ 318-р зүйл",
    link: "/contracts/checklist",
    action: "Чек-лист",
  },
  {
    icon: "🔔",
    title: "Гарах мэдэгдлийн эрх",
    desc: "Байрны эзэн та явахыг хүсвэл 30 хоногийн өмнө бичгээр мэдэгдэх үүрэгтэй. Гэнэт хөөж болохгүй.",
    law: "ИХ 204-р зүйл",
    link: "/contracts/generate",
    action: "Гэрээ үүсгэх",
  },
  {
    icon: "💰",
    title: "Барьцаа мөнгийн буцаалт",
    desc: "Байрыг гэмтэлгүй тушаасан бол барьцаа мөнгийг гэрээ дуусмагц буцааж авах эрхтэй.",
    law: "ИХ 318.4",
    link: "/contracts/tracker",
    action: "Гэрээ хянах",
  },
  {
    icon: "📍",
    title: "Бүртгэлийн эрх",
    desc: "Гэрээг Үл хөдлөх хөрөнгийн газарт бүртгүүлэх шаардлагатай. Бүртгэлгүй гэрээ хуулийн хүчин чадалгүй.",
    law: "ИХ 318.4",
    link: "/contracts/checklist",
    action: "Чек-лист",
  },
];

export default function LeasePage() {
  return (
    <div className="page-shell max-w-3xl">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Түрээслэгчийн эрхийн төв</h1>
        <p className="text-slate-500 text-sm max-w-lg mx-auto">
          Оюутан, залуус, түрээслэгчид гэрээ, байрны эрсдэл, хөөгдөлтөөс хамгаалах үндсэн заавар.
        </p>
      </div>

      {/* Rights grid */}
      <div className="grid md:grid-cols-2 gap-4 mb-8">
        {RIGHTS.map((r) => (
          <div key={r.title} className="card p-5">
            <div className="text-2xl mb-3">{r.icon}</div>
            <h3 className="font-semibold text-slate-900 mb-1">{r.title}</h3>
            <p className="text-sm text-slate-600 mb-3">{r.desc}</p>
            <div className="flex items-center justify-between">
              <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                {r.law}
              </span>
              <Link href={r.link} className="text-xs text-blue-600 hover:underline font-medium">
                {r.action} →
              </Link>
            </div>
          </div>
        ))}
      </div>

      {/* Core actions */}
      <div className="grid md:grid-cols-3 gap-3 mb-8">
        {[
          { href: "/contracts/generate", icon: "📄", label: "Гэрээ үүсгэх" },
          { href: "/contracts/checklist", icon: "☑️", label: "Чек-лист" },
          { href: "/contracts/tracker", icon: "📅", label: "Гэрээ хянах" },
        ].map((a) => (
          <Link key={a.href} href={a.href} className="card p-4 text-center hover:shadow-md transition-shadow group">
            <div className="text-2xl mb-1.5">{a.icon}</div>
            <div className="text-xs font-medium text-slate-700 group-hover:text-blue-700">{a.label}</div>
          </Link>
        ))}
      </div>

      {/* FAQ */}
      <div className="card p-5">
        <h2 className="section-title mb-4">Нийтлэг асуулт</h2>
        <div className="space-y-3">
          {[
            {
              q: "Байрны эзэн надыг гэрээ дуусахаас өмнө гаргах эрхтэй юу?",
              a: "Гэрээ дуусахаас өмнө байрны эзэн таныг гаргах бол заавал шалтгаан, хуульд заасан нөхцөл байх шаардлагатай. Шалтгаангүй гаргавал та хохирлоо шүүхээр барагдуулах эрхтэй.",
            },
            {
              q: "Барьцаа мөнгийг буцааж авахгүй бол яах вэ?",
              a: "Байрыг гэмтэлгүй буцааж өгсөн бол барьцаа мөнгөө шаардах хуулийн эрхтэй. Эхлээд бичгээр шаардлага гарга, хариу өгөхгүй бол шүүхэд гомдол гаргах боломжтой.",
            },
            {
              q: "Гэрээгүй байрлаж болох уу?",
              a: "Хуулийн хамгаалалт хамгийн сул байдаг тул гэрээгүй байрлахгүй байхыг зөвлөж байна. Маргаан гарсан үед гэрээгүй тохиолдолд нотлох баримтгүй болно.",
            },
          ].map((faq) => (
            <details key={faq.q} className="group">
              <summary className="cursor-pointer text-sm font-medium text-slate-800 py-2 flex items-center justify-between list-none">
                {faq.q}
                <span className="text-slate-400 group-open:rotate-180 transition-transform">▾</span>
              </summary>
              <p className="text-sm text-slate-600 pb-2 pt-1 leading-relaxed">{faq.a}</p>
            </details>
          ))}
        </div>
      </div>
    </div>
  );
}
