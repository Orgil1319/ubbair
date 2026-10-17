interface Props {
  date: string; // ISO date string
}

export default function DataFreshnessTag({ date }: Props) {
  const d = new Date(date);
  const diffDays = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
  const isStale = diffDays > 14;

  return (
    <span
      title={`Сүүлийн шинэчлэл: ${date}`}
      className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${
        isStale ? "bg-amber-50 text-amber-700 border border-amber-200" : "bg-slate-100 text-slate-500"
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${isStale ? "bg-amber-500" : "bg-green-500"}`} />
      {date}-нд шинэчлэгдсэн
    </span>
  );
}
