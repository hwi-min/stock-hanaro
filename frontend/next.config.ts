import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async rewrites() {
    const backendApiBaseUrl = process.env.BACKEND_API_BASE_URL;
    return backendApiBaseUrl
      ? [{ source: "/backend-api/:path*", destination: `${backendApiBaseUrl}/:path*` }]
      : [];
  },
};

export default nextConfig;
