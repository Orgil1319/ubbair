"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { generateContract } from "@/lib/api";

interface ContractFormData {
  // Landlord
  ownerName: string;
  ownerPhone: string;
  ownerEmail: string;
  ownerRegNum: string;
  // Tenant
  tenantName: string;
  tenantPhone: string;
  tenantEmail: string;
  tenantRegNum: string;
  // Property
  address: string;
  rooms: string;
  area: string;
  floor: string;
  // Terms
  startDate: string;
  endDate: string;
  monthlyRent: string;
  depositMonths: string;
  paymentDay: string;
  noticedays: string;
}

const EMPTY: ContractFormData = {
  ownerName: "", ownerPhone: "", ownerEmail: "", ownerRegNum: "",
  tenantName: "", tenantPhone: "", tenantEmail: "", tenantRegNum: "",
  address: "", rooms: "", area: "", floor: "",
  startDate: "", endDate: "", monthlyRent: "", depositMonths: "1",
  paymentDay: "1", noticedays: "30",
};

const InputField = ({ label, field, value, onChange, type = "text", placeholder = "" }: {
  label: string; field: keyof ContractFormData; value: string; onChange: (field: keyof ContractFormData, val: string) => void; type?: string; placeholder?: string;
}) => (
  <div>
    <label className="label">{label}</label>
    <input
      type={type}
      className="input"
      value={value}
      onChange={(e) => onChange(field, e.target.value)}
      placeholder={placeholder}
    />
  </div>
);

function ContractGenerateContent() {
  const router = useRouter();
  const params = useSearchParams();
  const [form, setForm] = useState<ContractFormData>({ ...EMPTY, address: params.get("address") ?? "" });
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pdfUrl, setPdfUrl] = useState("");

  const update = (field: keyof ContractFormData, value: string) =>
    setForm((f) => ({ ...f, [field]: value }));

  const REQUIRED: [keyof ContractFormData, string][] = [
    ["ownerName", "Эзний нэр"],
    ["ownerRegNum", "Эзний регистр"],
    ["ownerPhone", "Эзний утас"],
    ["tenantName", "Түрээслэгчийн нэр"],
    ["tenantRegNum", "Түрээслэгчийн регистр"],
    ["tenantPhone", "Түрээслэгчийн утас"],
    ["address", "Хаяг"],
    ["area", "Талбай"],
    ["startDate", "Эхлэх огноо"],
    ["endDate", "Дуусах огноо"],
    ["monthlyRent", "Сарын түрээс"],
  ];

  const handleGenerate = async () => {
    const missing = REQUIRED.filter(([field]) => !form[field].trim()).map(([, label]) => label);
    if (missing.length > 0) {
      setError(`Дутуу талбар: ${missing.join(", ")}`);
      return;
    }
    if (form.endDate <= form.startDate) {
      setError("Дуусах огноо эхлэх огнооноос хойш байх ёстой.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const payload = {
        owner: {
          full_name: form.ownerName,
          register_id: form.ownerRegNum,
          phone: form.ownerPhone,
          email: form.ownerEmail,
          address: form.address,
        },
        tenant: {
          full_name: form.tenantName,
          register_id: form.tenantRegNum,
          phone: form.tenantPhone,
          email: form.tenantEmail,
          address: form.address,
        },
        property_address: form.address,
        property_area_sqm: Number(form.area),
        monthly_rent: Number(form.monthlyRent),
        deposit: Number(form.depositMonths) * Number(form.monthlyRent),
        start_date: form.startDate,
        end_date: form.endDate,
        payment_day: Number(form.paymentDay),
        notice_days: Number(form.noticedays),
        rooms: form.rooms ? Number(form.rooms) : null,
      };

      const pdfBlob = await generateContract(payload);
      const url = URL.createObjectURL(pdfBlob);
      setPdfUrl(url);
      window.open(url, "_blank");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 mb-1">Түрээсийн гэрээ үүсгэх</h1>
        <p className="text-sm text-slate-500">Иргэний хуулийн 318-р зүйлд нийцсэн стандарт загвар</p>
      </div>

      {/* Steps */}
      <div className="flex items-center gap-2 mb-6">
        {[1, 2, 3].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-semibold ${
              step >= s ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-400"
            }`}>
              {s}
            </div>
            <span className={`text-xs ${step >= s ? "text-slate-700" : "text-slate-400"}`}>
              {s === 1 ? "Талуудын мэдээлэл" : s === 2 ? "Байрны мэдээлэл" : "Гэрээний нөхцөл"}
            </span>
            {s < 3 && <div className="w-6 h-px bg-slate-200" />}
          </div>
        ))}
      </div>

      <div className="card p-5">
        {step === 1 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-sm font-semibold text-slate-700 mb-3 pb-2 border-b border-slate-100">🏠 Байрны эзэн</h2>
              <div className="grid grid-cols-2 gap-3">
                <InputField label="Овог нэр" field="ownerName" value={form.ownerName} onChange={update} placeholder="Дорж Батаа" />
                <InputField label="Регистрийн дугаар" field="ownerRegNum" value={form.ownerRegNum} onChange={update} placeholder="АА12345678" />
                <InputField label="Утасны дугаар" field="ownerPhone" value={form.ownerPhone} onChange={update} type="tel" placeholder="9911 2233" />
                <InputField label="И-мэйл" field="ownerEmail" value={form.ownerEmail} onChange={update} type="email" placeholder="owner@example.com" />
              </div>
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-700 mb-3 pb-2 border-b border-slate-100">👤 Түрээслэгч</h2>
              <div className="grid grid-cols-2 gap-3">
                <InputField label="Овог нэр" field="tenantName" value={form.tenantName} onChange={update} placeholder="Батхүү Мөнх" />
                <InputField label="Регистрийн дугаар" field="tenantRegNum" value={form.tenantRegNum} onChange={update} placeholder="БА98765432" />
                <InputField label="Утасны дугаар" field="tenantPhone" value={form.tenantPhone} onChange={update} type="tel" placeholder="9922 3344" />
                <InputField label="И-мэйл" field="tenantEmail" value={form.tenantEmail} onChange={update} type="email" placeholder="tenant@example.com" />
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-700 mb-3">🏢 Байрны мэдээлэл</h2>
            <div className="col-span-2">
              <label className="label">Хаяг</label>
              <input type="text" className="input" value={form.address} onChange={(e) => update("address", e.target.value)} placeholder="Сүхбаатар дүүрэг, 1-р хороо, Энхтайваны өргөн чөлөө 10" />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <InputField label="Талбай (м²)" field="area" value={form.area} onChange={update} type="number" placeholder="52" />
              <InputField label="Өрөөний тоо" field="rooms" value={form.rooms} onChange={update} type="number" placeholder="2" />
              <InputField label="Давхар" field="floor" value={form.floor} onChange={update} type="number" placeholder="5" />
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-slate-700 mb-3">📋 Гэрээний нөхцөл</h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Эхлэх огноо</label>
                <input type="date" className="input" value={form.startDate} onChange={(e) => update("startDate", e.target.value)} />
              </div>
              <div>
                <label className="label">Дуусах огноо</label>
                <input type="date" className="input" value={form.endDate} onChange={(e) => update("endDate", e.target.value)} />
              </div>
              <InputField label="Сарын түрээс (₮)" field="monthlyRent" value={form.monthlyRent} onChange={update} type="number" placeholder="800000" />
              <div>
                <label className="label">Барьцаа мөнгө (сар)</label>
                <select className="input" value={form.depositMonths} onChange={(e) => update("depositMonths", e.target.value)}>
                  {[1, 2, 3].map((n) => <option key={n} value={n}>{n} сар</option>)}
                </select>
              </div>
              <div>
                <label className="label">Төлбөрийн өдөр</label>
                <select className="input" value={form.paymentDay} onChange={(e) => update("paymentDay", e.target.value)}>
                  {[1, 5, 10, 15, 20, 25].map((d) => <option key={d} value={d}>Сарын {d}-нд</option>)}
                </select>
              </div>
              <div>
                <label className="label">Урьдчилан мэдэгдэх хоног</label>
                <select className="input" value={form.noticedays} onChange={(e) => update("noticedays", e.target.value)}>
                  {[14, 30, 60].map((d) => <option key={d} value={d}>{d} хоног</option>)}
                </select>
              </div>
            </div>

            {/* Summary of legal protections */}
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 space-y-2 text-xs">
              <div className="font-semibold text-blue-900 text-sm mb-2">✅ Гэрээнд автоматаар оролцох заалтууд</div>
              {[
                "Барьцаа мөнгийг гэрээ дуусмагц 7 хоногт буцааж өгөх",
                `Гарахаас ${form.noticedays} хоногийн өмнө бичгээр мэдэгдэх үүрэг (ИХ 204-р зүйл)`,
                "Байрны эзний буруутай үйлдлээс гарсан бол нөхөн төлбөргүй гарах эрх",
                "Гэрээг Үл хөдлөх хөрөнгийн газарт бүртгүүлэх зааварчилгаа (ИХ 318.4)",
              ].map((item) => (
                <div key={item} className="flex items-start gap-1.5 text-blue-800">
                  <span className="shrink-0">•</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex justify-between mt-4">
        {step > 1 ? (
          <button onClick={() => setStep(step - 1)} className="btn-secondary">← Буцах</button>
        ) : <div />}
        {step < 3 ? (
          <button onClick={() => setStep(step + 1)} className="btn-primary">Үргэлжлүүлэх →</button>
        ) : (
          <button onClick={handleGenerate} className="btn-primary" disabled={loading}>
            {loading ? "Үүсгэж байна..." : "📄 Гэрээ үүсгэх"}
          </button>
        )}
      </div>

      {error && (
        <div className="card p-4 mt-4 bg-red-50 border-red-200 text-sm text-red-700">{error}</div>
      )}

      {pdfUrl && (
        <div className="card p-4 mt-4 bg-green-50 border-green-200 text-sm text-green-800 space-y-2">
          <div className="font-semibold">Гэрээ бэлэн боллоо.</div>
          <div className="flex flex-wrap gap-3">
            <a href={pdfUrl} download="lease_contract.pdf" className="btn-secondary text-sm">📄 PDF татах</a>
            <button onClick={() => router.push("/contracts/tracker")} className="btn-primary text-sm">
              Миний гэрээнүүд →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ContractGeneratePage() {
  return (
    <Suspense>
      <ContractGenerateContent />
    </Suspense>
  );
}
