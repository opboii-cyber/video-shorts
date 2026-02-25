import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import AuthProvider from "@/components/AuthProvider";
import Navbar from "@/components/Navbar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "VideoShorts — Turn Long Videos Into Viral Shorts",
    description:
        "AI-powered video clipping. Upload a video, and our AI finds the best moment, tracks the speaker, and crops it to a perfect 9:16 vertical short.",
    keywords: "video shorts, AI video editor, vertical video, TikTok, Reels, Shorts, face tracking",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className="dark">
            <body className={`${inter.className} bg-gray-950 text-white antialiased`}>
                <AuthProvider>
                    <Navbar />
                    {children}
                </AuthProvider>
            </body>
        </html>
    );
}
