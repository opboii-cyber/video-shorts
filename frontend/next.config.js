/** @type {import('next').NextConfig} */
const nextConfig = {
    // Allow images/videos from the backend API
    async rewrites() {
        return [
            {
                source: "/api/:path*",
                destination: "http://localhost:8000/api/:path*",
            },
        ];
    },
};

module.exports = nextConfig;
