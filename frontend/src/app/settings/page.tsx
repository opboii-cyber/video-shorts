"use client";

import { useSession, signOut } from "next-auth/react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authFetch } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Settings Page — Account info, plan, API keys.
 */
export default function SettingsPage() {
    const { data: session, status } = useSession();
    const router = useRouter();
    const [credits, setCredits] = useState(0);
    const [plan, setPlan] = useState("free");
    const [payments, setPayments] = useState<any[]>([]);
    const [apiKey, setApiKey] = useState("vsk_••••••••••••••••");
    const [showKey, setShowKey] = useState(false);

    useEffect(() => {
        if (status === "unauthenticated") router.push("/login");
    }, [status, router]);

    useEffect(() => {
        if (status === "authenticated") loadUsage();
    }, [status]);

    const loadUsage = async () => {
        try {
            const res = await authFetch(`${API}/api/payments/usage`);
            if (res.ok) {
                const data = await res.json();
                setCredits(data.credits_remaining);
                setPlan(data.plan);
                setPayments(data.payments || []);
            }
        } catch (err) {
            console.error("Failed to load usage:", err);
        }
    };

    if (status === "loading") {
        return (
            <div className="min-h-screen bg-gray-950 pt-20 flex items-center justify-center">
                <div className="w-12 h-12 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <main className="min-h-screen bg-gray-950 text-white pt-20 px-4">
            <div className="max-w-3xl mx-auto py-8">
                <h1 className="text-3xl font-bold mb-8">Settings</h1>

                {/* Account Section */}
                <section className="mb-8 bg-gray-800/60 backdrop-blur-sm rounded-2xl p-6 border border-gray-700/50">
                    <h2 className="text-lg font-bold mb-4">Account</h2>
                    <div className="space-y-4">
                        <div className="flex items-center gap-4">
                            {session?.user?.image ? (
                                <img src={session.user.image} alt="" className="w-14 h-14 rounded-full" />
                            ) : (
                                <div className="w-14 h-14 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-2xl font-bold">
                                    {session?.user?.name?.[0] || "U"}
                                </div>
                            )}
                            <div>
                                <div className="font-medium text-lg">{session?.user?.name || "User"}</div>
                                <div className="text-gray-400 text-sm">{session?.user?.email}</div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Plan & Credits */}
                <section className="mb-8 bg-gray-800/60 backdrop-blur-sm rounded-2xl p-6 border border-gray-700/50">
                    <h2 className="text-lg font-bold mb-4">Plan & Usage</h2>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="bg-gray-700/30 rounded-xl p-4">
                            <div className="text-sm text-gray-400">Current Plan</div>
                            <div className="text-2xl font-bold capitalize mt-1">{plan}</div>
                        </div>
                        <div className="bg-gray-700/30 rounded-xl p-4">
                            <div className="text-sm text-gray-400">Credits Remaining</div>
                            <div className="text-2xl font-bold mt-1 bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
                                {credits}
                            </div>
                        </div>
                    </div>
                    <a
                        href="/pricing"
                        className="mt-4 inline-block px-4 py-2 rounded-lg bg-indigo-500/10 text-indigo-400 text-sm hover:bg-indigo-500/20 transition-colors"
                    >
                        Upgrade Plan →
                    </a>
                </section>

                {/* API Key Section */}
                <section className="mb-8 bg-gray-800/60 backdrop-blur-sm rounded-2xl p-6 border border-gray-700/50">
                    <h2 className="text-lg font-bold mb-4">API Access</h2>
                    <p className="text-gray-400 text-sm mb-4">
                        Use your API key to process videos programmatically. Available on Agency plan.
                    </p>
                    <div className="flex items-center gap-2">
                        <input
                            type="text"
                            value={showKey ? "vsk_live_" + session?.user?.email?.replace(/[@.]/g, "_") : apiKey}
                            readOnly
                            className="flex-1 px-4 py-2 rounded-lg bg-gray-700/50 border border-gray-600 text-sm font-mono text-gray-300"
                        />
                        <button
                            onClick={() => setShowKey(!showKey)}
                            className="px-4 py-2 rounded-lg bg-gray-700 text-sm hover:bg-gray-600 transition-colors"
                        >
                            {showKey ? "Hide" : "Show"}
                        </button>
                    </div>
                </section>

                {/* Payment History */}
                {payments.length > 0 && (
                    <section className="mb-8 bg-gray-800/60 backdrop-blur-sm rounded-2xl p-6 border border-gray-700/50">
                        <h2 className="text-lg font-bold mb-4">Payment History</h2>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="text-gray-400 text-left">
                                        <th className="pb-3 font-medium">Date</th>
                                        <th className="pb-3 font-medium">Plan</th>
                                        <th className="pb-3 font-medium">Credits</th>
                                        <th className="pb-3 font-medium text-right">Amount</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {payments.map((p: any) => (
                                        <tr key={p.id} className="border-t border-gray-700/30">
                                            <td className="py-3 text-gray-300">
                                                {p.date ? new Date(p.date).toLocaleDateString() : "—"}
                                            </td>
                                            <td className="py-3 text-gray-300 capitalize">{p.plan}</td>
                                            <td className="py-3 text-gray-300">{p.credits}</td>
                                            <td className="py-3 text-right text-gray-300">${p.amount?.toFixed(2)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </section>
                )}

                {/* Danger Zone */}
                <section className="bg-gray-800/60 backdrop-blur-sm rounded-2xl p-6 border border-red-500/20">
                    <h2 className="text-lg font-bold mb-4 text-red-400">Danger Zone</h2>
                    <button
                        onClick={() => signOut({ callbackUrl: "/" })}
                        className="px-4 py-2 rounded-lg bg-red-500/10 text-red-400 text-sm hover:bg-red-500/20 transition-colors"
                    >
                        Sign Out
                    </button>
                </section>
            </div>
        </main>
    );
}
