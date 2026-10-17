"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login, setAuthSession } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await login({ email, password });
      setAuthSession(response.token, response.user);
      router.push(response.user.is_admin ? "/admin" : "/ads");
    } catch (err) {
      setError((err as Error).message || "Нэвтрэхэд алдаа гарлаа");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="page-shell py-16">
      <div className="max-w-md mx-auto bg-white rounded-3xl border border-slate-200 shadow-xl p-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Нэвтрэх</h1>
        <p className="text-sm text-slate-500 mb-6">Зар оруулах, өөрийн зурга, зарын статустай танилцахын тулд нэвтэрнэ үү.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Имэйл</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input mt-2"
              required
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Нууц үг</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input mt-2"
              required
            />
          </label>

          {error && <div className="text-sm text-red-600">{error}</div>}

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Хүлээх..." : "Нэвтрэх"}
          </button>
        </form>

        <p className="mt-6 text-sm text-slate-500">
          Шинэ хэрэглэгч үү? <Link href="/register" className="text-blue-600 hover:underline">Бүртгүүлэх</Link>
        </p>
      </div>
    </main>
  );
}
