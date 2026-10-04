import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit .next/standalone (server.js + minimal node_modules) for production Docker container
  output: "standalone",
};

export default nextConfig;
