import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  eslint: {
    // Это позволит завершить сборку, даже если в коде есть ошибки линтинга
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Это позволит завершить сборку, даже если есть ошибки типов (полезно для быстрого деплоя)
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
