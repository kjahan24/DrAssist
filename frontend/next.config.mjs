/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  output: "standalone",
  eslint: {
    dirs: ["src"],
  },
  images: {
    remotePatterns: [],
  },
};

export default nextConfig;
