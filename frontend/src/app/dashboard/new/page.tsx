"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import { authFetch } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * New Short — Upload a video and create a new vertical short.
 */
export default function NewShortPage() {
    const { status } = useSession();
    const router = useRouter();
    const [step, setStep] = useState<"upload" | "processing" | "done">("upload");
    const [file, setFile] = useState<File | null>(null);
    const [youtubeUrl, setYoutubeUrl] = useState("");
    const [dragActive, setDragActive] = useState(false);
    const [jobId, setJobId] = useState<string | null>(null);
    const [progress, setProgress] = useState(0);
    const [jobStatus, setJobStatus] = useState("");
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState("");
    const pollRef = useRef<NodeJS.Timeout>();

    useEffect(() => {
        if (status === "unauthenticated") router.push("/login");
    }, [status, router]);

    // Poll job status
    useEffect(() => {
        if (jobId && step === "processing") {
            pollRef.current = setInterval(async () => {
                try {
                    const res = await authFetch(`${API}/api/jobs/${jobId}`);
                    if (res.ok) {
                        const data = await res.json();
                        setProgress(data.progress || 0);
                        setJobStatus(data.status);

                        if (data.status === "completed") {
                            clearInterval(pollRef.current);
                            setResult(data);
                            setStep("done");
                        } else if (data.status === "failed") {
                            clearInterval(pollRef.current);
                            setError(data.error || "Processing failed");
                            setStep("upload");
                        }
                    }
                } catch (err) {
                    console.error("Poll error:", err);
                }
            }, 2000);
        }

        return () => clearInterval(pollRef.current);
    }, [jobId, step]);

    const handleUpload = async () => {
        if (!file && !youtubeUrl) return;
        setError("");

        try {
            // Step 1: Upload the video
            const formData = new FormData();
            if (file) {
                formData.append("file", file);
            } else {
                formData.append("youtube_url", youtubeUrl);
            }

            const uploadRes = await authFetch(`${API}/api/upload`, {
                method: "POST",
                body: formData,
            });

            if (!uploadRes.ok) {
                const data = await uploadRes.json();
                throw new Error(data.detail || "Upload failed");
            }

            const uploadData = await uploadRes.json();

            // Step 2: Create a processing job
            const jobRes = await authFetch(`${API}/api/jobs`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    video_path: uploadData.video_path,
                    source_type: uploadData.source,
                }),
            });

            if (!jobRes.ok) {
                const data = await jobRes.json();
                throw new Error(data.detail || "Failed to create job");
            }

            const jobData = await jobRes.json();
            setJobId(jobData.job_id);
            setStep("processing");
        } catch (err: any) {
            setError(err.message);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragActive(false);
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile?.type.startsWith("video/")) {
            setFile(droppedFile);
        }
    };

    const stageLabels: Record<string, string> = {
        pending: "Queued...",
        transcribing: "Transcribing audio...",
        finding_hook: "AI finding best moment...",
        cropping: "Cropping to vertical...",
        rendering: "Rendering final video...",
    };

    return (
        <main className="min-h-screen bg-gray-950 text-white pt-20 px-4">
            <div className="max-w-2xl mx-auto py-12">
                <h1 className="text-3xl font-bold mb-2">Create New Short</h1>
                <p className="text-gray-400 mb-8">Upload a video and let AI do the rest.</p>

                {error && (
                    <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                        {error}
                    </div>
                )}

                {/* ── UPLOAD STEP ──────────────────────────────────── */}
                {step === "upload" && (
                    <>
                        {/* Drag and Drop Zone */}
                        <div
                            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                            onDragLeave={() => setDragActive(false)}
                            onDrop={handleDrop}
                            className={`
                border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer
                ${dragActive
                                    ? "border-indigo-500 bg-indigo-500/5"
                                    : "border-gray-700 hover:border-gray-600 bg-gray-800/20"
                                }
              `}
                            onClick={() => document.getElementById("file-input")?.click()}
                        >
                            <input
                                id="file-input"
                                type="file"
                                accept="video/*"
                                className="hidden"
                                onChange={(e) => setFile(e.target.files?.[0] || null)}
                            />
                            <svg className="w-12 h-12 text-gray-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                            {file ? (
                                <p className="text-indigo-400 font-medium">{file.name}</p>
                            ) : (
                                <>
                                    <p className="text-gray-400">Drop a video file here, or click to browse</p>
                                    <p className="text-xs text-gray-600 mt-2">MP4, MOV, AVI, MKV — up to 500 MB</p>
                                </>
                            )}
                        </div>

                        {/* Divider */}
                        <div className="flex items-center my-6">
                            <div className="flex-1 border-t border-gray-700" />
                            <span className="px-4 text-gray-500 text-sm">or</span>
                            <div className="flex-1 border-t border-gray-700" />
                        </div>

                        {/* YouTube URL */}
                        <input
                            type="url"
                            placeholder="Paste a YouTube URL"
                            value={youtubeUrl}
                            onChange={(e) => setYoutubeUrl(e.target.value)}
                            className="w-full px-4 py-3 rounded-xl bg-gray-800/50 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
                        />

                        {/* Submit */}
                        <button
                            onClick={handleUpload}
                            disabled={!file && !youtubeUrl}
                            className="mt-6 w-full py-3 rounded-xl font-semibold bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 disabled:opacity-40 transition-all"
                        >
                            Generate Short →
                        </button>
                    </>
                )}

                {/* ── PROCESSING STEP ─────────────────────────────── */}
                {step === "processing" && (
                    <div className="text-center py-16">
                        <div className="relative w-24 h-24 mx-auto mb-8">
                            <div className="w-24 h-24 border-4 border-gray-700 rounded-full" />
                            <div
                                className="absolute inset-0 w-24 h-24 border-4 border-transparent border-t-indigo-500 rounded-full animate-spin"
                            />
                            <div className="absolute inset-0 flex items-center justify-center text-xl font-bold">
                                {progress}%
                            </div>
                        </div>

                        <h2 className="text-xl font-bold mb-2">
                            {stageLabels[jobStatus] || "Processing..."}
                        </h2>
                        <p className="text-gray-400 text-sm">This usually takes 30-90 seconds</p>

                        {/* Progress bar */}
                        <div className="mt-8 max-w-sm mx-auto">
                            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                        </div>

                        {/* Step indicators */}
                        <div className="mt-8 flex justify-center gap-8 text-xs">
                            {["Upload", "Transcribe", "Find hook", "Crop", "Done"].map((label, i) => {
                                const percent = (i + 1) * 20;
                                const active = progress >= percent - 15;
                                return (
                                    <div key={label} className={`${active ? "text-indigo-400" : "text-gray-600"} transition-colors`}>
                                        {label}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* ── DONE STEP ───────────────────────────────────── */}
                {step === "done" && result && (
                    <div className="text-center">
                        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-green-500/10 border border-green-500/20 mb-6">
                            <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            <span className="text-sm text-green-400">Short created!</span>
                        </div>

                        <h2 className="text-2xl font-bold mb-2">{result.title || "Your Short"}</h2>

                        {result.output_path && (
                            <div className="mt-6 max-w-xs mx-auto">
                                <video
                                    src={`${API}/${result.output_path}`}
                                    controls
                                    className="w-full aspect-[9/16] rounded-xl bg-gray-800"
                                />
                            </div>
                        )}

                        <div className="mt-8 flex gap-4 justify-center">
                            <a
                                href={result.output_path ? `${API}/${result.output_path}` : "#"}
                                download
                                className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 font-medium"
                            >
                                Download
                            </a>
                            <button
                                onClick={() => { setStep("upload"); setFile(null); setYoutubeUrl(""); setResult(null); }}
                                className="px-6 py-3 rounded-xl bg-gray-800 border border-gray-700 text-gray-300 font-medium hover:bg-gray-700"
                            >
                                Create Another
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </main>
    );
}
