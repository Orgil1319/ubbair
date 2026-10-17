import type { Metadata } from "next";
import "@fontsource-variable/inter";
// @ts-ignore: side-effect import of global CSS without type declarations
import "./globals.css";

export const metadata: Metadata = {
  title: "УБ Байр — Аюулгүй байрны зөвлөгч",
  description:
    "Улаанбаатар хотод байр худалдаж авах, түрээслэхэд эрсдэлийн үнэлгээ, хуулийн зөвлөгөө, луйварын анхааруулга.",
  keywords: ["байр", "үл хөдлөх хөрөнгө", "Улаанбаатар", "эрсдэл", "түрээс"],
};

import AIChatbot from "@/components/AIChatbot";
import Sidebar from "@/components/Sidebar";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="mn">
      <body className="bg-slate-50 text-slate-900 antialiased flex min-h-screen">
        <Sidebar />
        <main className="flex-1 md:ml-64 pt-14 md:pt-0 min-w-0 relative">
          {children}
        </main>
        <AIChatbot />
      </body>
    </html>
  );
}
