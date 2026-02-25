/**
 * auth.ts — Auth helpers & session provider
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Get the JWT token from NextAuth session for API calls.
 */
export async function getAuthToken(): Promise<string | null> {
    try {
        const res = await fetch("/api/auth/session");
        const session = await res.json();
        // NextAuth stores the token in the session
        return session?.accessToken || null;
    } catch {
        return null;
    }
}

/**
 * Authenticated fetch wrapper — adds Bearer token to requests.
 */
export async function authFetch(
    url: string,
    options: RequestInit = {}
): Promise<Response> {
    const token = await getAuthToken();

    const headers: HeadersInit = {
        ...(options.headers || {}),
    };

    if (token) {
        (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
    }

    return fetch(url, { ...options, headers });
}
