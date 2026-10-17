type RiskLevel = "low" | "medium" | "high";

interface Props {
  level: RiskLevel;
  size?: "sm" | "md" | "lg";
}

const CONFIG: Record<RiskLevel, { label: string; icon: string; cls: string }> = {
  low: { label: "Аюулгүй", icon: "🟢", cls: "bg-green-100 text-green-800 border-green-200" },
  medium: { label: "Дунд", icon: "🟡", cls: "bg-amber-100 text-amber-800 border-amber-200" },
  high: { label: "Эрсдэлтэй", icon: "🔴", cls: "bg-red-100 text-red-800 border-red-200" },
};

export default function RiskBadge({ level, size = "md" }: Props) {
  const c = CONFIG[level];
  const sizeClass = size === "sm" ? "text-xs px-1.5 py-0.5" : size === "lg" ? "text-sm px-3 py-1.5" : "text-xs px-2 py-1";
  return (
    <span className={`inline-flex items-center gap-1 font-medium rounded-full border whitespace-nowrap ${c.cls} ${sizeClass}`}>
      {c.icon} {c.label}
    </span>
  );
}
