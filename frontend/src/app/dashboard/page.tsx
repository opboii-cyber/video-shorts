"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import JobCard from "@/components/JobCard";
import { authFetch } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Dashboard — User's processed shorts, usage stats, and quick actions.
 */
export default function DashboardPage() {
    const { data: session, status } = useSession();
    const router = useRouter();
    const [jobs, setJobs] = useState<any[]>([]);
    const [credits, setCredits] = useState(0);
    const [plan, setPlan] = useState("free");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (status === "unauthenticated") {
            router.push("/login");
        }
    }, [status, router]);

    useEffect(() => {
        if (status === "authenticated") {
            loadData();
        }
    }, [status]);

    const loadData = async () => {
        try {
            // Load jobs
            const jobsRes = await authFetch(`${API}/api/jobs`);
            if (jobsRes.ok) {
                const data = await jobsRes.json();
                setJobs(data.jobs);
            }

            // Load usage
            const usageRes = await authFetch(`${API}/api/payments/usage`);
            if (usageRes.ok) {
                const data = await usageRes.json();
                setCredits(data.credits_remaining);
                setPlan(data.plan);
            }
        } catch (err) {
            console.error("Failed to load dashboard data:", err);
        } finally {
            setLoading(false);
        }
    };

    if (status === "loading" || loading) {
        return (
            <div className="min-h-screen bg-gray-950 pt-20 flex items-center justify-center">
                <div className="w-12 h-12 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <main className="min-h-screen bg-gray-950 text-white pt-20 px-4 sm:px-6 lg:px-8">
            <div className="max-w-7xl mx-auto py-8">
                {/* Header */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
                    <div>
                        <h1 className="text-3xl font-bold">Dashboard</h1>
                        <p className="text-gray-400 mt-1">Welcome back, {session?.user?.name || "Creator"}</p>
                    </div>
                    <Link
                        href="/dashboard/new"
                        className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 font-medium transition-all shadow-lg shadow-indigo-500/25"
                    >
                        + Create New Short
                    </Link>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
                    <div className="bg-gray-800/60 backdrop-blur-sm rounded-xl p-5 border border-gray-700/50">
                        <div className="text-sm text-gray-400">Credits Remaining</div>
                        <div className="text-3xl font-bold mt-1 bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
                            {credits}
                        </div>
                        <Link href="/pricing" className="text-xs text-indigo-400 hover:text-indigo-300 mt-2 inline-block">
                            Get more →
                        </Link>
                    </div>
                    <div className="bg-gray-800/60 backdrop-blur-sm rounded-xl p-5 border border-gray-700/50">
                        <div className="text-sm text-gray-400">Total Shorts Created</div>
                        <div className="text-3xl font-bold mt-1 text-white">
                            {jobs.filter(j => j.status === "completed").length}
                        </div>
                    </div>
                    <div className="bg-gray-800/60 backdrop-blur-sm rounded-xl p-5 border border-gray-700/50">
                        <div className="text-sm text-gray-400">Current Plan</div>
                        <div className="text-3xl font-bold mt-1 text-white capitalize">{plan}</div>
                        {plan === "free" && (
                            <Link href="/pricing" className="text-xs text-indigo-400 hover:text-indigo-300 mt-2 inline-block">
                                Upgrade →
                            </Link>
                        )}
                    </div>
                </div>

                {/* Jobs Grid */}
                <h2 className="text-xl font-bold mb-4">Your Shorts</h2>

                {jobs.length === 0 ? (
                    <div className="text-center py-20 bg-gray-800/30 rounded-2xl border border-gray-700/30">
                        <svg className="w-16 h-16 text-gray-600 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
                        </svg>
                        <h3 className="text-lg font-medium text-gray-400">No shorts yet</h3>
                        <p className="text-gray-500 mt-1 mb-6">Upload a video to create your first viral short</p>
                        <Link
                            href="/dashboard/new"
                            className="inline-block px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 font-medium"
                        >
                            Create Your First Short
                        </Link>
                    </div>
                ) : (
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                        {jobs.map((job) => (
                            <JobCard key={job.id} job={job} />
                        ))}
                    </div>
                )}
            </div>
        </main>
    );
}
