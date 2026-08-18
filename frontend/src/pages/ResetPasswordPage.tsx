import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { Field, FormError, PrimaryButton } from "@/components/Form";
import { formatAuthError } from "@/lib/api";
import { confirmPasswordReset } from "@/lib/api";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const [token, setToken] = useState(searchParams.get("token") ?? "");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setSubmitting(true);
    try {
      const result = await confirmPasswordReset(token, password);
      setMessage(result.message);
    } catch (caught) {
      setError(formatAuthError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="max-w-md">
      <h1 className="font-display text-3xl">Choose a new password</h1>
      <form className="mt-8 flex flex-col gap-5" onSubmit={(event) => void onSubmit(event)}>
        <FormError message={error} />
        {message ? (
          <p className="rounded-sm border border-rule bg-paper-2 px-4 py-3" role="status">
            {message}{" "}
            <Link to="/login" className="underline">
              Log in
            </Link>
          </p>
        ) : null}
        <Field
          label="Reset token"
          name="token"
          required
          value={token}
          onChange={(event) => setToken(event.target.value)}
        />
        <Field
          label="New password"
          name="password"
          type="password"
          autoComplete="new-password"
          minLength={10}
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <PrimaryButton disabled={submitting}>
          {submitting ? "Updating…" : "Update password"}
        </PrimaryButton>
      </form>
    </section>
  );
}
