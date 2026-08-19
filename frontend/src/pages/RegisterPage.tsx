import { FormEvent, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { Field, FormError, PrimaryButton } from "@/components/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { formatAuthError } from "@/lib/api";

export function RegisterPage() {
  const { user, loading, register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!loading && user) {
    return <Navigate to="/settings/account" replace />;
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(email, password);
    } catch (caught) {
      setError(formatAuthError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="max-w-md">
      <h1 className="font-display text-3xl">Create an account</h1>
      <p className="mt-2 text-ink-soft">
        PaceLab is a private friends beta, not a general public product. Your running data is stored
        against this account. Passwords are hashed with Argon2id.
      </p>
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
          autoComplete="new-password"
          minLength={10}
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          hint="At least 10 characters."
        />
        <PrimaryButton disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </PrimaryButton>
      </form>
      <p className="mt-6 text-sm text-ink-soft">
        Already registered?{" "}
        <Link to="/login" className="underline">
          Log in
        </Link>
        .
      </p>
    </section>
  );
}
