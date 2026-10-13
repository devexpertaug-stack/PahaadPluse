"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { setSession } from "@/lib/auth";
import { Button } from "@/components/ui/Button";
import {
  DEMO_LOGIN_HINT,
  DEMO_OWNER_PASSWORD,
  DEMO_OWNER_USERNAME,
} from "@/lib/demoCredentials";

/**
 * The branded sign-in form. Posts to `/auth/login`, stores the session token +
 * user on success and redirects to the dashboard home. Shows an inline error on
 * failure. Kept as its own client component so it is easy to unit test.
 */
export function LoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { token, user } = await api.login(username, password);
      setSession(token, user);
      // Routing: '/' is the immersive landing, '/login' is auth, and the
      // gated product home now lives at '/dashboard'.
      router.push("/dashboard");
    } catch {
      setError("Invalid username or password. Please try again.");
      setSubmitting(false);
    }
  }

  function fillDemoCredentials() {
    setUsername(DEMO_OWNER_USERNAME);
    setPassword(DEMO_OWNER_PASSWORD);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" aria-label="Sign in form">
      <div className="space-y-1.5">
        <label
          htmlFor="username"
          className="block text-sm font-semibold text-forest-800"
        >
          Email or username
        </label>
        <input
          id="username"
          name="username"
          type="text"
          autoComplete="username"
          required
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="owner@forestseason.demo"
          className="w-full rounded-xl border border-mist-300 bg-mist-white/90 px-4 py-2.5 text-slate-800 shadow-sm outline-none transition focus:border-forest-400 focus:ring-2 focus:ring-forest-300"
        />
      </div>

      <div className="space-y-1.5">
        <label
          htmlFor="password"
          className="block text-sm font-semibold text-forest-800"
        >
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••••••"
          className="w-full rounded-xl border border-mist-300 bg-mist-white/90 px-4 py-2.5 text-slate-800 shadow-sm outline-none transition focus:border-forest-400 focus:ring-2 focus:ring-forest-300"
        />
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-xl border border-alert-200 bg-alert-50 px-4 py-2.5 text-sm font-medium text-alert-600"
        >
          {error}
        </p>
      )}

      <Button
        type="submit"
        variant="primary"
        disabled={submitting}
        className="w-full py-2.5 text-base"
      >
        {submitting ? "Signing in…" : "Sign in"}
      </Button>

      <button
        type="button"
        onClick={fillDemoCredentials}
        className="w-full rounded-xl border border-dashed border-sky-300 bg-sky-50/70 px-4 py-2.5 text-left text-xs text-slate-600 transition hover:border-sky-400 hover:bg-sky-50"
      >
        <span className="font-semibold text-sky-700">Demo credentials</span>
        <br />
        {DEMO_LOGIN_HINT}
      </button>
    </form>
  );
}
