import type { NextConfig } from "next";

// `standalone` is for Docker only — Vercel uses its own Next.js builder.
const nextConfig: NextConfig = {
  ...(process.env.DOCKER_BUILD === "true" ? { output: "standalone" as const } : {}),
};

export default nextConfig;
