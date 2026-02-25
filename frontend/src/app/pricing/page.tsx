"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import PricingCards from "@/components/PricingCards";
import { authFetch } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Pricing Page — Display plans and handle Stripe checkout.
 */
export default function PricingPage() {
    const { data: session } = useSession();
    const [loading, setLoading] = useState(false);

    const handleSelectPlan = async (plan: string) => {
        if (!session) {
            window.location.href = "/login";
            return;
        }

        setLoading(true);

        try {
            const res = await authFetch(`${API}/api/payments/checkout`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ plan }),
            });

            if (res.ok) {
                const data = await res.json();
                window.location.href = data.checkout_url;
            } else {
                const data = await res.json();
                alert(data.detail || "Checkout failed");
            }
        } catch (err) {
            alert("Failed to create checkout session");
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="min-h-screen bg-gray-950 text-white pt-20 px-4">
            <div className="max-w-6xl mx-auto py-16">
                <div className="text-center mb-16">
                    <h1 className="text-4xl sm:text-5xl font-bold mb-4">
                        Simple,{" "}
                        <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
                            Transparent
                        </span>{" "}
                        Pricing
                    </h1>
                    <p className="text-lg text-gray-400 max-w-xl mx-auto">
                        No subscriptions. No hidden fees. Buy credits and use them whenever you want.
                    </p>
                </div>

                <PricingCards onSelectPlan={handleSelectPlan} loading={loading} />

                {/* FAQ Section */}
                <div className="mt-24 max-w-2xl mx-auto">
                    <h2 className="text-2xl font-bold text-center mb-10">Frequently Asked Questions</h2>
                    {[
                        {
                            q: "Do credits expire?",
                            a: "No, credits never expire. Use them at your own pace.",
                        },
                        {
                            q: "What counts as one credit?",
                            a: "One credit = one processed short. Upload a video, get a vertical short, and one credit is used.",
                        },
                        {
                            q: "Can I get a refund?",
                            a: "Yes, we offer a 7-day money-back guarantee if you're not satisfied. Contact support.",
                        },
                        {
                            q: "Do you offer an API?",
                            a: "Yes! Agency plan includes API access. You'll get an API key in your settings.",
                        },
                    ].map((faq) => (
                        <div key={faq.q} className="mb-6 p-5 bg-gray-800/40 rounded-xl border border-gray-700/30">
                            <h3 className="font-medium text-white mb-2">{faq.q}</h3>
                            <p className="text-gray-400 text-sm">{faq.a}</p>
                        </div>
                    ))}
                </div>
            </div>
        </main>
    );
}
