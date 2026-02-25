"use client";

/**
 * JobCard — Displays a single processed short in the dashboard.
 */

interface Job {
    id: string;
    status: string;
    progress: number;
    title: string;
    output_path?: string;
    created_at?: string;
    completed_at?: string;
    duration?: number;
    error?: string;
}

interface JobCardProps {
    job: Job;
}

const statusColors: Record<string, string> = {
    pending: "bg-yellow-500/20 text-yellow-400",
    transcribing: "bg-blue-500/20 text-blue-400",
    finding_hook: "bg-purple-500/20 text-purple-400",
    cropping: "bg-indigo-500/20 text-indigo-400",
    rendering: "bg-cyan-500/20 text-cyan-400",
    completed: "bg-green-500/20 text-green-400",
    failed: "bg-red-500/20 text-red-400",
};

export default function JobCard({ job }: JobCardProps) {
    const statusClass = statusColors[job.status] || "bg-gray-500/20 text-gray-400";

    return (
        <div className="bg-gray-800/60 backdrop-blur-sm rounded-xl border border-gray-700/50 p-5 hover:border-gray-600/50 transition-all group">
            {/* Thumbnail area or status indicator */}
            <div className="aspect-[9/16] bg-gray-700/30 rounded-lg mb-4 flex items-center justify-center overflow-hidden">
                {job.status === "completed" && job.output_path ? (
                    <video
                        src={`http://localhost:8000/${job.output_path}`}
                        className="w-full h-full object-cover rounded-lg"
                        muted
                        playsInline
                        onMouseEnter={(e) => (e.target as HTMLVideoElement).play()}
                        onMouseLeave={(e) => {
                            const v = e.target as HTMLVideoElement;
                            v.pause();
                            v.currentTime = 0;
                        }}
                    />
                ) : job.status === "failed" ? (
                    <svg className="w-12 h-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                ) : (
                    <div className="text-center">
                        <div className="w-12 h-12 mx-auto mb-2 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                        <span className="text-xs text-gray-400">{job.progress}%</span>
                    </div>
                )}
            </div>

            {/* Info */}
            <h3 className="font-medium text-white truncate">{job.title || "Processing..."}</h3>

            <div className="flex items-center justify-between mt-2">
                <span className={`text-xs px-2 py-1 rounded-full font-medium ${statusClass}`}>
                    {job.status.replace("_", " ")}
                </span>
                {job.duration && (
                    <span className="text-xs text-gray-500">{Math.round(job.duration)}s</span>
                )}
            </div>

            {job.created_at && (
                <p className="text-xs text-gray-500 mt-2">
                    {new Date(job.created_at).toLocaleDateString()}
                </p>
            )}

            {job.error && (
                <p className="text-xs text-red-400 mt-2 truncate" title={job.error}>
                    {job.error}
                </p>
            )}

            {/* Download button */}
            {job.status === "completed" && job.output_path && (
                <a
                    href={`http://localhost:8000/${job.output_path}`}
                    download
                    className="mt-3 w-full block text-center py-2 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-sm font-medium transition-all opacity-0 group-hover:opacity-100"
                >
                    Download
                </a>
            )}
        </div>
    );
}
