interface Props {
  startDate: string;
  endDate: string;
}

export default function LeaseTimeline({ startDate, endDate }: Props) {
  const start = new Date(startDate).getTime();
  const end = new Date(endDate).getTime();
  const now = Date.now();

  const total = end - start;
  const elapsed = Math.min(now - start, total);
  const progress = Math.max(0, Math.min(100, (elapsed / total) * 100));

  const warn30 = end - 30 * 24 * 60 * 60 * 1000;
  const warn7 = end - 7 * 24 * 60 * 60 * 1000;
  const warn30Pct = Math.max(0, Math.min(100, ((warn30 - start) / total) * 100));
  const warn7Pct = Math.max(0, Math.min(100, ((warn7 - start) / total) * 100));

  const fmt = (d: string) => new Date(d).toLocaleDateString("mn-MN", { month: "short", day: "numeric", year: "numeric" });

  return (
    <div>
      {/* Bar */}
      <div className="relative h-3 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="absolute left-0 top-0 h-full bg-blue-500 rounded-full transition-all"
          style={{ width: `${progress}%` }}
        />
        {/* 30-day warning marker */}
        <div
          className="absolute top-0 w-0.5 h-full bg-amber-400 opacity-70"
          style={{ left: `${warn30Pct}%` }}
          title="30 хоног үлдэнэ"
        />
        {/* 7-day warning marker */}
        <div
          className="absolute top-0 w-0.5 h-full bg-red-400 opacity-70"
          style={{ left: `${warn7Pct}%` }}
          title="7 хоног үлдэнэ"
        />
      </div>

      {/* Labels */}
      <div className="flex justify-between mt-1.5 text-xs text-slate-400">
        <span>{fmt(startDate)}</span>
        <div className="flex gap-3">
          <span className="text-amber-500">━ 30 хоног</span>
          <span className="text-red-500">━ 7 хоног</span>
        </div>
        <span>{fmt(endDate)}</span>
      </div>
    </div>
  );
}
