import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  turbopack: {
    // Set root to the octavia-web directory to resolve build correctly
    root: __dirname,
  },
};

export default nextConfig;
