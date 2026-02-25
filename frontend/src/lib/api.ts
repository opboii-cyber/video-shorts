/**
 * api.ts — Fetch helpers for the backend API.
 *
 * TODO: Implement actual API calls once backend endpoints are wired.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function uploadVideo(file: File): Promise<any> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: formData,
    });

    if (!res.ok) throw new Error("Upload failed");
    return res.json();
}

export async function uploadYoutubeUrl(url: string): Promise<any> {
    const formData = new FormData();
    formData.append("youtube_url", url);

    const res = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: formData,
    });

    if (!res.ok) throw new Error("Upload failed");
    return res.json();
}

export async function processVideo(videoPath: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_path: videoPath }),
    });

    if (!res.ok) throw new Error("Processing failed");
    return res.json();
}

export async function healthCheck(): Promise<boolean> {
    try {
        const res = await fetch(`${API_BASE}/api/health`);
        return res.ok;
    } catch {
        return false;
    }
}
