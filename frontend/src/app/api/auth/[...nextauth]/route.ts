import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import GitHubProvider from "next-auth/providers/github";
import CredentialsProvider from "next-auth/providers/credentials";

/**
 * NextAuth.js Configuration
 *
 * Supports:
 *  - Google OAuth
 *  - GitHub OAuth
 *  - Email/password (credentials — for demo/dev)
 *
 * Uses JWT strategy (stateless — no session DB needed).
 * The JWT is sent to the FastAPI backend in the Authorization header.
 */
const handler = NextAuth({
    providers: [
        GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID || "",
            clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
        }),
        GitHubProvider({
            clientId: process.env.GITHUB_CLIENT_ID || "",
            clientSecret: process.env.GITHUB_CLIENT_SECRET || "",
        }),
        // Demo credentials provider (for development without OAuth setup)
        CredentialsProvider({
            name: "Email",
            credentials: {
                email: { label: "Email", type: "email", placeholder: "you@example.com" },
                password: { label: "Password", type: "password" },
            },
            async authorize(credentials) {
                // TODO: Replace with real DB lookup
                if (credentials?.email && credentials?.password) {
                    return {
                        id: credentials.email,
                        email: credentials.email,
                        name: credentials.email.split("@")[0],
                    };
                }
                return null;
            },
        }),
    ],

    session: {
        strategy: "jwt",
        maxAge: 30 * 24 * 60 * 60, // 30 days
    },

    callbacks: {
        async jwt({ token, user }) {
            if (user) {
                token.id = user.id;
                token.email = user.email;
                token.name = user.name;
                token.picture = user.image;
            }
            return token;
        },
        async session({ session, token }) {
            if (session.user) {
                (session.user as any).id = token.id;
            }
            return session;
        },
    },

    pages: {
        signIn: "/login",
    },

    secret: process.env.NEXTAUTH_SECRET || "your-secret-key-change-in-production",
});

export { handler as GET, handler as POST };
