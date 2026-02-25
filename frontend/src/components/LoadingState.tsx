"use client";

/**
 * LoadingState — Animated processing indicator.
 *
 * Shows a pulsing animation while the backend processes the video.
 */
export default function LoadingState() {
    return (
        <div className="flex flex-col items-center justify-center py-20">
            {/* Animated spinner */}
            <div className="relative w-24 h-24 mb-8">
                <div className="absolute inset-0 rounded-full border-4 border-indigo-500/20" />
                <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-indigo-500 animate-spin" />
                <div className="absolute inset-3 rounded-full border-4 border-transparent border-t-purple-500 animate-spin" style={{ animationDuration: "1.5s" }} />
            </div>

            <h2 className="text-2xl font-semibold text-white mb-2">
                Processing your video...
            </h2>

            {/* Step indicators */}
            <div className="mt-6 space-y-3 text-sm text-gray-400">
                {[
                    "🎙️ Extracting audio & transcribing...",
                    "🧠 Finding the best hook...",
                    "👁️ Tracking faces & cropping...",
                    "🎬 Rendering vertical short...",
                ].map((step, i) => (
                    <div key={i} className="flex items-center gap-2 animate-pulse" style={{ animationDelay: `${i * 0.3}s` }}>
                        <span>{step}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
