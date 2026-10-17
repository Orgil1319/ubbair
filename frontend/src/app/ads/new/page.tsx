"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createAd } from "@/lib/api";

export default function NewAdPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [address, setAddress] = useState("");
  const [price, setPrice] = useState("");
  const [area, setArea] = useState("");
  const [rooms, setRooms] = useState(1);
  const [propertyType, setPropertyType] = useState("apartment");
  const [photo, setPhoto] = useState<File | null>(null);
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const body = new FormData();
      body.append("title", title);
      body.append("description", description);
      body.append("address", address);
      body.append("price", String(price));
      body.append("area_sqm", String(area));
      body.append("rooms", String(rooms));
      body.append("property_type", propertyType);
      if (photo) body.append("photo", photo);
      if (latitude) body.append("latitude", latitude);
      if (longitude) body.append("longitude", longitude);

      await createAd(body);
      router.push("/ads");
    } catch (err) {
      setError((err as Error).message || "Зар оруулахад алдаа гарлаа");
    } finally {
      setLoading(false);
    }
  };

  const fillCurrentLocation = () => {
    if (!navigator.geolocation) {
      setError("Таны браузер байршлыг дэмждэггүй.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude.toString());
        setLongitude(position.coords.longitude.toString());
        setError("");
      },
      () => {
        setError("Байршлыг олж чадаагүй. Дахин оролдоно уу.");
      },
      { timeout: 10000 }
    );
  };

  return (
    <main className="page-shell py-10">
      <div className="max-w-3xl mx-auto bg-white rounded-3xl border border-slate-200 shadow-xl p-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Зар оруулах</h1>
        <p className="text-sm text-slate-500 mb-6">Таны байрны зарын ерөнхий мэдээллийг оруулж, админ зөвшөөрөхийг хүлээнэ.</p>

        <form onSubmit={handleSubmit} className="space-y-5">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Гарчиг</span>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="input mt-2"
              required
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Тайлбар</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input mt-2 min-h-[140px] resize-none"
              required
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Хаяг</span>
            <input
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="input mt-2"
              required
            />
          </label>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Үнэ (₮)</span>
              <input
                type="number"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="input mt-2"
                required
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Талбай (м²)</span>
              <input
                type="number"
                value={area}
                onChange={(e) => setArea(e.target.value)}
                className="input mt-2"
                required
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Өрөө</span>
              <input
                type="number"
                value={rooms}
                onChange={(e) => setRooms(Number(e.target.value))}
                className="input mt-2"
                min={1}
                required
              />
            </label>
          </div>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Барилгын төрөл</span>
            <select
              value={propertyType}
              onChange={(e) => setPropertyType(e.target.value)}
              className="input mt-2"
            >
              <option value="apartment">Орон сууц</option>
              <option value="house">Гэр</option>
              <option value="land">Газар</option>
            </select>
          </label>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Зураг</span>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
                className="input mt-2"
              />
            </label>
            <div className="grid grid-cols-2 gap-4">
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Latitude</span>
                <input
                  type="text"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  className="input mt-2"
                  placeholder="47.9210"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Longitude</span>
                <input
                  type="text"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  className="input mt-2"
                  placeholder="106.9186"
                />
              </label>
            </div>
          </div>
          <button
            type="button"
            className="btn-secondary w-full"
            onClick={fillCurrentLocation}
          >
            Миний байршлыг авах
          </button>

          {error && <div className="text-sm text-red-600">{error}</div>}

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Илгээх..." : "Зар оруулах"}
          </button>
        </form>
      </div>
    </main>
  );
}
