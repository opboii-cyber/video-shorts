"use client";

import Link from "next/link";
import { useSession, signOut } from "next-auth/react";
import { useState } from "react";

/**
 * Navbar — Shared navigation bar with auth-aware state.
 *
 * Shows:
 *  - Logo + brand
 *  - Navigation links
 *  - Login button (unauthenticated) or user avatar (authenticated)
 */
export default function Navbar() {
    const { data: session } = useSession();
    const [menuOpen, setMenuOpen] = useState(false);

    return (
        <nav className="fixed top-0 left-0 right-0 z-50 bg-gray-900/80 backdrop-blur-xl border-b border-gray-800/50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
                            VideoShorts
                        </span>
                    </Link>

                    {/* Desktop Nav */}
                    <div className="hidden md:flex items-center gap-6">
                        <Link href="/pricing" className="text-gray-300 hover:text-white transition-colors text-sm font-medium">
                            Pricing
                        </Link>
                        {session ? (
                            <>
                                <Link href="/dashboard" className="text-gray-300 hover:text-white transition-colors text-sm font-medium">
                                    Dashboard
                                </Link>
                                <Link href="/dashboard/new" className="text-gray-300 hover:text-white transition-colors text-sm font-medium">
                                    Create Short
                                </Link>
                                <div className="relative">
                                    <button
                                        onClick={() => setMenuOpen(!menuOpen)}
                                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
                                    >
                                        {session.user?.image ? (
                                            <img src={session.user.image} alt="" className="w-6 h-6 rounded-full" />
                                        ) : (
                                            <div className="w-6 h-6 rounded-full bg-indigo-500 flex items-center justify-center text-xs font-bold">
                                                {session.user?.name?.[0] || "U"}
                                            </div>
                                        )}
                                        <span className="text-sm text-gray-300">{session.user?.name || "Account"}</span>
                                    </button>
                                    {menuOpen && (
                                        <div className="absolute right-0 mt-2 w-48 py-2 bg-gray-800 rounded-xl border border-gray-700 shadow-xl">
                                            <Link href="/settings" className="block px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 transition-colors">
                                                Settings
                                            </Link>
                                            <button
                                                onClick={() => signOut({ callbackUrl: "/" })}
                                                className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-gray-700 transition-colors"
                                            >
                                                Sign out
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </>
                        ) : (
                            <Link
                                href="/login"
                                className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white text-sm font-medium transition-all"
                            >
                                Get Started
                            </Link>
                        )}
                    </div>

                    {/* Mobile hamburger */}
                    <button
                        onClick={() => setMenuOpen(!menuOpen)}
                        className="md:hidden p-2 rounded-lg text-gray-400 hover:text-white"
                    >
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={menuOpen ? "M6 18L18 6M6 6l12 12" : "M4 6h16M4 12h16M4 18h16"} />
                        </svg>
                    </button>
                </div>
            </div>
        </nav>
    );
}
