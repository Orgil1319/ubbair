import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/gis/:path*",
        destination: `${process.env.API_URL ?? "http://localhost:8000"}/gis/:path*`,
      },
      {
        source: "/api/contracts/:id/pdf",
        destination: `${process.env.API_URL ?? "http://localhost:8000"}/contracts/:id/pdf`,
      },
    ];
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.unegui.mn" },
    ],
  },
};

export default nextConfig;
