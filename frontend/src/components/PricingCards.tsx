"use client";

/**
 * PricingCards — Reusable pricing tiers component.
 *
 * Shows Starter / Pro / Agency plans with features and CTA buttons.
 */

interface PricingCardProps {
    onSelectPlan?: (plan: string) => void;
    loading?: boolean;
}

const plans = [
    {
        id: "starter",
        name: "Starter",
        price: "$9.99",
        period: "one-time",
        credits: 15,
        features: [
            "15 video shorts",
            "AI face tracking",
            "720p output quality",
            "Basic hook detection",
            "Email support",
        ],
        popular: false,
        gradient: "from-blue-500 to-cyan-500",
    },
    {
        id: "pro",
        name: "Pro",
        price: "$29.99",
        period: "one-time",
        credits: 50,
        features: [
            "50 video shorts",
            "AI face tracking",
            "1080p output quality",
            "Advanced hook detection",
            "Priority processing",
            "Custom branding",
            "Priority support",
        ],
        popular: true,
        gradient: "from-indigo-500 to-purple-500",
    },
    {
        id: "agency",
        name: "Agency",
        price: "$79.99",
        period: "one-time",
        credits: 200,
        features: [
            "200 video shorts",
            "AI face tracking",
            "4K output quality",
            "Premium hook detection",
            "Fastest processing",
            "White-label option",
            "API access",
            "Dedicated support",
        ],
        popular: false,
        gradient: "from-purple-500 to-pink-500",
    },
];

export default function PricingCards({ onSelectPlan, loading }: PricingCardProps) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto">
            {plans.map((plan) => (
                <div
                    key={plan.id}
                    className={`
            relative rounded-2xl p-[1px] transition-transform hover:scale-105
            ${plan.popular
                            ? `bg-gradient-to-br ${plan.gradient} shadow-2xl shadow-indigo-500/20`
                            : "bg-gray-700/50"
                        }
          `}
                >
                    {plan.popular && (
                        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 text-xs font-bold uppercase tracking-wider">
                            Most Popular
                        </div>
                    )}

                    <div className="bg-gray-900 rounded-2xl p-8 h-full flex flex-col">
                        {/* Header */}
                        <h3 className={`text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r ${plan.gradient}`}>
                            {plan.name}
                        </h3>

                        <div className="mt-4">
                            <span className="text-4xl font-extrabold text-white">{plan.price}</span>
                            <span className="text-gray-400 ml-2">/ {plan.credits} shorts</span>
                        </div>

                        {/* Features */}
                        <ul className="mt-6 space-y-3 flex-1">
                            {plan.features.map((feature) => (
                                <li key={feature} className="flex items-start gap-3 text-sm text-gray-300">
                                    <svg className={`w-5 h-5 mt-0.5 flex-shrink-0 bg-clip-text text-transparent bg-gradient-to-r ${plan.gradient}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" className={`stroke-current ${plan.popular ? 'text-indigo-400' : 'text-gray-500'}`} />
                                    </svg>
                                    {feature}
                                </li>
                            ))}
                        </ul>

                        {/* CTA */}
                        <button
                            onClick={() => onSelectPlan?.(plan.id)}
                            disabled={loading}
                            className={`
                mt-8 w-full py-3 rounded-xl font-semibold transition-all
                ${plan.popular
                                    ? `bg-gradient-to-r ${plan.gradient} hover:opacity-90 text-white`
                                    : "bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700"
                                }
                disabled:opacity-40
              `}
                        >
                            {loading ? "Processing..." : `Get ${plan.name}`}
                        </button>
                    </div>
                </div>
            ))}
        </div>
    );
}
