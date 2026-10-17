import type { BlacklistResult } from "@/lib/api";

interface Props {
  company: BlacklistResult;
}

export default function CompanyWarning({ company }: Props) {
  return (
    <div className="card border-red-300 bg-red-50 p-5">
      <div className="flex items-start gap-3 mb-4">
        <div className="text-3xl">🚨</div>
        <div>
          <div className="font-bold text-red-900 text-lg">Анхааруулга!</div>
          <p className="text-sm text-red-700 mt-1">
            Энэ компани хар жагсаалтад орсон байна. Гэрээ байгуулахаасаа өмнө нарийвчлан шалгана уу.
          </p>
        </div>
      </div>

      <div className="space-y-2">
        {company.entries?.map((entry, i) => (
          <div key={i} className="bg-white border border-red-200 rounded-lg p-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-red-900">{entry.companyName}</div>
                <div className="text-xs text-red-600 mt-0.5">{entry.reason}</div>
              </div>
              <span className="text-xs text-red-500 whitespace-nowrap shrink-0">{entry.source}</span>
            </div>
            {entry.details && (
              <p className="text-xs text-slate-600 mt-2 border-t border-red-100 pt-2">{entry.details}</p>
            )}
            <div className="text-xs text-slate-400 mt-1">Жагсаалтад орсон: {entry.listedDate}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 bg-white border border-red-200 rounded-lg p-3 text-xs text-red-700">
        <strong>Дараах алхам авахыг зөвлөж байна:</strong>
        <ul className="mt-1.5 space-y-1 list-disc list-inside">
          <li>НХБХГ-т биечлэн очиж баталгаажуулах</li>
          <li>Хуульч эсвэл мэргэжлийн зуучаар дамжуулах</li>
          <li>Барилгын зөвшөөрлийг шалгах</li>
        </ul>
      </div>
    </div>
  );
}
