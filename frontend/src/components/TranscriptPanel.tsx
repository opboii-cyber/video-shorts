"use client";

/**
 * TranscriptPanel — Displays the timestamped transcript beside the video.
 *
 * TODO: Add click-to-seek (clicking a segment jumps the video player).
 */
interface Segment {
    start: number;
    end: number;
    text: string;
}

interface Props {
    transcript: { segments: Segment[] } | null;
}

function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function TranscriptPanel({ transcript }: Props) {
    if (!transcript) return null;

    return (
        <div className="flex flex-col">
            <h2 className="text-xl font-semibold mb-4 text-gray-300">
                📝 Transcript
            </h2>
            <div className="bg-gray-800/50 rounded-2xl p-6 space-y-3 max-h-[600px] overflow-y-auto">
                {transcript.segments.map((seg, i) => (
                    <div
                        key={i}
                        className="flex gap-3 p-2 rounded-lg hover:bg-gray-700/50 transition-colors cursor-pointer"
                    >
                        <span className="text-indigo-400 font-mono text-sm whitespace-nowrap mt-0.5">
                            {formatTime(seg.start)}
                        </span>
                        <p className="text-gray-300 text-sm">{seg.text}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}
