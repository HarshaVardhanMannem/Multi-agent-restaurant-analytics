/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Optimize lucide-react imports for Next.js 15
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
  // Enable standalone output for Docker
  output: 'standalone',
}

module.exports = nextConfig
