"use client";

import { useRef, useState } from "react";

/**
 * VideoPlayer — Custom HTML5 video player for the vertical short.
 *
 * Displays the 9:16 result with basic controls.
 * TODO: Add timeline scrubbing, speed control, download button.
 */
interface Props {
    src: string;
}

export default function VideoPlayer({ src }: Props) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [isPlaying, setIsPlaying] = useState(false);

    const togglePlay = () => {
        if (!videoRef.current) return;
        if (isPlaying) {
            videoRef.current.pause();
        } else {
            videoRef.current.play();
        }
        setIsPlaying(!isPlaying);
    };

    return (
        <div className="flex flex-col items-center">
            <h2 className="text-xl font-semibold mb-4 text-gray-300">
                🎥 Your Vertical Short
            </h2>
            <div className="relative rounded-2xl overflow-hidden bg-black shadow-2xl" style={{ aspectRatio: "9/16", maxHeight: "600px" }}>
                <video
                    ref={videoRef}
                    src={src}
                    className="w-full h-full object-contain"
                    onEnded={() => setIsPlaying(false)}
                    controls
                />
            </div>
            <button
                onClick={togglePlay}
                className="mt-4 px-6 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors text-sm"
            >
                {isPlaying ? "⏸ Pause" : "▶ Play"}
            </button>
        </div>
    );
}
