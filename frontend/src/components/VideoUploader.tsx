"use client";

import { useState, useRef, DragEvent } from "react";

/**
 * VideoUploader — Drag-and-drop + YouTube URL input.
 *
 * TODO: Wire up actual file upload to the backend.
 */
interface Props {
    onGenerate: (file: File | null, youtubeUrl: string) => void;
}

export default function VideoUploader({ onGenerate }: Props) {
    const [file, setFile] = useState<File | null>(null);
    const [youtubeUrl, setYoutubeUrl] = useState("");
    const [isDragging, setIsDragging] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleDrop = (e: DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        const dropped = e.dataTransfer.files[0];
        if (dropped?.type.startsWith("video/")) setFile(dropped);
    };

    return (
        <div className="max-w-2xl mx-auto">
            {/* Drop zone */}
            <div
                className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors ${isDragging
                        ? "border-indigo-400 bg-indigo-400/10"
                        : "border-gray-600 hover:border-gray-400"
                    }`}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
            >
                <input
                    ref={inputRef}
                    type="file"
                    accept="video/*"
                    className="hidden"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                <p className="text-gray-400 text-lg">
                    {file ? `✓ ${file.name}` : "Drop a video file here or click to browse"}
                </p>
            </div>

            {/* OR divider */}
            <div className="flex items-center my-6">
                <div className="flex-1 border-t border-gray-700" />
                <span className="px-4 text-gray-500 text-sm">OR</span>
                <div className="flex-1 border-t border-gray-700" />
            </div>

            {/* YouTube URL */}
            <input
                type="url"
                placeholder="Paste a YouTube URL..."
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />

            {/* Generate button */}
            <button
                onClick={() => onGenerate(file, youtubeUrl)}
                disabled={!file && !youtubeUrl}
                className="w-full mt-6 py-4 rounded-xl font-semibold text-lg bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
                🎬 Generate Short
            </button>
        </div>
    );
}
