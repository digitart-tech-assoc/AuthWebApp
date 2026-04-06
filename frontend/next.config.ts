import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  // ホストマシンから WebSocket HMR にアクセスできるように許可
  allowedDevOrigins: ["localhost", "127.0.0.1"],
};

export default nextConfig;
