import { FormEvent, useState } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";

import { Field, FormError, PrimaryButton } from "@/components/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { formatAuthError } from "@/lib/api";

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  if (!loading && user) {
    return <Navigate to={from} replace />;
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (caught) {
      setError(formatAuthError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="max-w-md">
      <h1 className="font-display text-3xl">Log in</h1>
      <p className="mt-2 text-ink-soft">Use your PaceLab email and password.</p>
      <form className="mt-8 flex flex-col gap-5" onSubmit={(event) => void onSubmit(event)}>
        <FormError message={error} />
        <Field
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <PrimaryButton disabled={submitting}>{submitting ? "Signing in…" : "Log in"}</PrimaryButton>
      </form>
      <p className="mt-6 text-sm text-ink-soft">
        <Link to="/forgot-password" className="underline">
          Forgot password?
        </Link>
      </p>
      <p className="mt-2 text-sm text-ink-soft">
        Need an account?{" "}
        <Link to="/register" className="underline">
          Create one
        </Link>
        .
      </p>
    </section>
  );
}
