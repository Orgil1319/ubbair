"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearAuthSession, getStoredAuthUser, isAuthenticated, logout } from "@/lib/api";

const BASE_NAV_ITEMS = [
  { href: "/", label: "Нүүр", icon: "🏠" },
  { href: "/search", label: "Байр хайх", icon: "🔍" },
  { href: "/ads", label: "Миний зар", icon: "📣" },
  { href: "/blacklist", label: "Хар жагсаалт", icon: "⚠️" },
  { href: "/lease", label: "Түрээс", icon: "🔑" },
  { href: "/contracts/generate", label: "Гэрээ үүсгэх", icon: "📄" },
  { href: "/admin", label: "Админ", icon: "🛠️" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [loggedIn, setLoggedIn] = useState(false);
  const [user, setUser] = useState(getStoredAuthUser());

  useEffect(() => {
    const syncAuthState = () => {
      setLoggedIn(isAuthenticated());
      setUser(getStoredAuthUser());
    };

    syncAuthState();
    window.addEventListener("auth-state-changed", syncAuthState);
    return () => window.removeEventListener("auth-state-changed", syncAuthState);
  }, []);

  const navItems = BASE_NAV_ITEMS.filter((item) => {
    if (item.href === "/admin/pending") {
      return Boolean(user?.is_admin);
    }
    return true;
  });

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      clearAuthSession();
    }
    router.push("/");
  };

  return (
    <aside className="w-64 fixed inset-y-0 left-0 bg-white border-r border-slate-200 shadow-sm flex flex-col z-50">
      {/* Header */}
      <div className="h-16 flex items-center px-6 border-b border-slate-100">
        <button 
          onClick={() => router.back()} 
          className="mr-3 p-1.5 rounded-lg hover:bg-slate-100 transition-colors text-slate-500 hover:text-slate-900"
          title="Буцах"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="m15 18-6-6 6-6"/>
          </svg>
        </button>
        <Link href="/" className="font-bold text-lg text-blue-600 flex items-center gap-2 tracking-tight">
          УБ Байр
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-1.5">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                isActive 
                  ? "bg-blue-50 text-blue-700 shadow-sm border border-blue-100/50" 
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <span className="text-lg opacity-80">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer info */}
      <div className="p-4 border-t border-slate-100 bg-slate-50/50 mt-auto space-y-3">
        {loggedIn ? (
          <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
            <p className="text-[11px] font-semibold text-slate-700">Профайл</p>
            <p className="mt-1 text-sm font-semibold text-slate-900">{user?.name || user?.email || "Хэрэглэгч"}</p>
            <p className="text-xs text-slate-500">{user?.email}</p>
            <button
              type="button"
              onClick={handleLogout}
              className="mt-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
            >
              Гарах
            </button>
          </div>
        ) : (
          <Link
            href="/login"
            className="flex items-center justify-center rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-700 transition hover:bg-blue-100"
          >
            Нэвтрэх
          </Link>
        )}

        <div className="bg-white rounded-xl p-3 border border-slate-200 shadow-sm flex items-start gap-2.5">
          <div className="text-lg">🤖</div>
          <div>
            <p className="text-[11px] font-semibold text-slate-700">AI Зөвлөх</p>
            <p className="text-[10px] text-slate-500 mt-0.5 leading-tight">Байр худалдан авахтай холбоотой бүх эрсдэл, зөвлөгөө.</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
