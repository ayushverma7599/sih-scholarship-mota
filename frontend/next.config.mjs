/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Proxy /api/* to the FastAPI backend so the browser can call same-origin.
    const backend = process.env.BACKEND_ORIGIN || "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};
export default nextConfig;
