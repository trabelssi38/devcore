import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    const apiUrl = process.env.DEVCORE_API_URL || "http://api:20131";
    const dashboardUrl = process.env.DEVCORE_DASHBOARD_URL || "http://dashboard-api:20129";
    return [
      // Proxy devcore-api endpoints (health, tasks, workflows, etc.)
      { source: "/proxy/api/:path*", destination: `${apiUrl}/api/:path*` },
      // Proxy dashboard endpoints (dashboard data + SSE stream)
      { source: "/proxy/dashboard/:path*", destination: `${dashboardUrl}/api/:path*` },
    ];
  },
};

export default nextConfig;

