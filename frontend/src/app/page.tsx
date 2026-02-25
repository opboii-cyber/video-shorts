"use client";

import Link from "next/link";
import PricingCards from "@/components/PricingCards";

/**
 * Landing Page — Hero, features, demo, pricing preview, and CTA.
 */
export default function LandingPage() {
    return (
        <main className="min-h-screen bg-gray-950 text-white">
            {/* ═══════════════════════════════════════════════════════
          HERO SECTION
          ═══════════════════════════════════════════════════════ */}
            <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
                {/* Animated background blobs */}
                <div className="absolute inset-0 overflow-hidden">
                    <div className="absolute -top-40 -left-40 w-80 h-80 bg-indigo-500/20 rounded-full blur-3xl animate-pulse" />
                    <div className="absolute top-1/3 -right-20 w-96 h-96 bg-purple-500/15 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "1s" }} />
                    <div className="absolute bottom-20 left-1/4 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "2s" }} />
                </div>

                {/* Grid pattern overlay */}
                <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0wIDBoNDB2NDBIMHoiLz48cGF0aCBkPSJNNDAgMEgwdjQwaDQwVjB6TTEgMWgzOHYzOEgxVjF6IiBmaWxsPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMDMpIi8+PC9nPjwvc3ZnPg==')] opacity-40" />

                <div className="relative z-10 text-center max-w-4xl mx-auto px-4">
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 mb-8">
                        <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                        <span className="text-sm text-indigo-300">AI-Powered Video Clipping</span>
                    </div>

                    <h1 className="text-5xl sm:text-7xl font-extrabold leading-tight">
                        Turn Long Videos Into{" "}
                        <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">
                            Viral Shorts
                        </span>
                    </h1>

                    <p className="mt-6 text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed">
                        Upload any landscape video. Our AI finds the most engaging moment,
                        tracks the speaker&apos;s face, and delivers a perfectly cropped
                        9:16 vertical short — ready for TikTok, Reels, and Shorts.
                    </p>

                    <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link
                            href="/login"
                            className="px-8 py-4 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white font-semibold text-lg transition-all shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40"
                        >
                            Start Creating — Free
                        </Link>
                        <Link
                            href="#features"
                            className="px-8 py-4 rounded-xl bg-gray-800/50 border border-gray-700 text-gray-300 hover:bg-gray-700/50 font-medium text-lg transition-all"
                        >
                            See How It Works
                        </Link>
                    </div>

                    <p className="mt-4 text-sm text-gray-500">3 free shorts • No credit card required</p>
                </div>

                {/* Scroll indicator */}
                <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
                    <svg className="w-6 h-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                    </svg>
                </div>
            </section>

            {/* ═══════════════════════════════════════════════════════
          HOW IT WORKS
          ═══════════════════════════════════════════════════════ */}
            <section id="features" className="py-24 px-4">
                <div className="max-w-6xl mx-auto">
                    <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
                        Three Steps to{" "}
                        <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
                            Viral Content
                        </span>
                    </h2>
                    <p className="text-gray-400 text-center max-w-xl mx-auto mb-16">
                        Our AI pipeline handles everything from transcription to export.
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {[
                            {
                                step: "01",
                                icon: "🎙️",
                                title: "Upload & Transcribe",
                                desc: "Drop a video or paste a YouTube URL. Our AI transcribes every word with precise timestamps using Whisper.",
                                gradient: "from-blue-500 to-cyan-500",
                            },
                            {
                                step: "02",
                                icon: "🎯",
                                title: "AI Finds the Hook",
                                desc: "GPT-4o / Claude analyses the transcript to find the most engaging 30-60 second segment — the hook that stops the scroll.",
                                gradient: "from-indigo-500 to-purple-500",
                            },
                            {
                                step: "03",
                                icon: "✂️",
                                title: "Smart Crop & Export",
                                desc: "Face tracking with Kalman filter smoothing intelligently crops the video to 9:16 vertical format — ready to post.",
                                gradient: "from-purple-500 to-pink-500",
                            },
                        ].map((item) => (
                            <div
                                key={item.step}
                                className="relative group p-8 rounded-2xl bg-gray-900/50 border border-gray-800/50 hover:border-gray-700/50 transition-all"
                            >
                                <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br ${item.gradient} text-2xl mb-4`}>
                                    {item.icon}
                                </div>
                                <div className="text-xs text-gray-500 font-mono mb-2">STEP {item.step}</div>
                                <h3 className="text-xl font-bold mb-3">{item.title}</h3>
                                <p className="text-gray-400 leading-relaxed">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ═══════════════════════════════════════════════════════
          STATS BAR
          ═══════════════════════════════════════════════════════ */}
            <section className="py-16 border-y border-gray-800/50">
                <div className="max-w-6xl mx-auto px-4 grid grid-cols-2 md:grid-cols-4 gap-8">
                    {[
                        { value: "3×", label: "Faster than manual editing" },
                        { value: "95%", label: "Face tracking accuracy" },
                        { value: "< 60s", label: "Average processing time" },
                        { value: "9:16", label: "Perfect vertical format" },
                    ].map((stat) => (
                        <div key={stat.label} className="text-center">
                            <div className="text-3xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
                                {stat.value}
                            </div>
                            <div className="text-sm text-gray-500 mt-1">{stat.label}</div>
                        </div>
                    ))}
                </div>
            </section>

            {/* ═══════════════════════════════════════════════════════
          PRICING SECTION
          ═══════════════════════════════════════════════════════ */}
            <section className="py-24 px-4" id="pricing">
                <div className="max-w-6xl mx-auto">
                    <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
                        Simple, Transparent Pricing
                    </h2>
                    <p className="text-gray-400 text-center max-w-xl mx-auto mb-16">
                        Start free. Upgrade when you need more shorts.
                    </p>

                    <PricingCards onSelectPlan={() => window.location.href = "/login"} />
                </div>
            </section>

            {/* ═══════════════════════════════════════════════════════
          FINAL CTA
          ═══════════════════════════════════════════════════════ */}
            <section className="py-24 px-4">
                <div className="max-w-3xl mx-auto text-center">
                    <h2 className="text-3xl sm:text-4xl font-bold mb-6">
                        Ready to Go Viral?
                    </h2>
                    <p className="text-gray-400 mb-10">
                        Join thousands of creators using VideoShorts to grow their audience on every platform.
                    </p>
                    <Link
                        href="/login"
                        className="inline-block px-10 py-4 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white font-semibold text-lg transition-all shadow-lg shadow-indigo-500/25"
                    >
                        Get Started Free →
                    </Link>
                </div>
            </section>

            {/* ═══════════════════════════════════════════════════════
          FOOTER
          ═══════════════════════════════════════════════════════ */}
            <footer className="border-t border-gray-800/50 py-12 px-4">
                <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="text-gray-500 text-sm">
                        © 2026 VideoShorts. All rights reserved.
                    </div>
                    <div className="flex items-center gap-6 text-sm text-gray-500">
                        <a href="#" className="hover:text-white transition-colors">Terms</a>
                        <a href="#" className="hover:text-white transition-colors">Privacy</a>
                        <a href="#" className="hover:text-white transition-colors">Contact</a>
                    </div>
                </div>
            </footer>
        </main>
    );
}
