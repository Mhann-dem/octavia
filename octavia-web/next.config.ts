import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  turbopack: {
    // Set root to the octavia-web directory to resolve build correctly
    root: __dirname,
  },
  // Add a dev-time proxy rewrite to forward API calls to the backend
  // Set env var NEXT_PUBLIC_USE_DEV_PROXY=true in .env.local to enable
  async rewrites() {
    const backend = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001').replace(/\/$/, '');
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backend}/api/v1/:path*`,
      },
      {
        // some code may call /api/:path* — also proxy that to backend root
        source: '/api/:path*',
        destination: `${backend}/api/:path*`,
      },
      {
        // Verify endpoint used by email links
        source: '/verify',
        destination: `${backend}/verify`,
      },
      {
        // Proxy auth endpoints so client can POST to same-origin paths
        source: '/login',
        destination: `${backend}/login`,
      },
      {
        source: '/signup',
        destination: `${backend}/signup`,
      },
      {
        source: '/logout',
        destination: `${backend}/logout`,
      },
    ];
  },
};

export default nextConfig;
