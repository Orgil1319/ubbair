import type { Metadata } from "next";
import { Inter, Noto_Sans_Mongolian } from "next/font/google";
// @ts-ignore: side-effect import of global CSS without type declarations
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const notoMongolian = Noto_Sans_Mongolian({
  subsets: ["latin"],
  variable: "--font-mongolian",
  weight: "400",
});

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
    <html lang="mn" className={`${inter.variable} ${notoMongolian.variable}`}>
      <body className="bg-slate-50 text-slate-900 antialiased flex min-h-screen">
        <Sidebar />
        <main className="flex-1 ml-64 min-w-0 relative">
          {children}
        </main>
        <AIChatbot />
      </body>
    </html>
  );
}
