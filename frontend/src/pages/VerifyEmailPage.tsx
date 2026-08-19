import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { Field, FormError, PrimaryButton } from "@/components/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { formatAuthError, verifyEmail } from "@/lib/api";

export function VerifyEmailPage() {
  const { refresh } = useAuth();
  const [searchParams] = useSearchParams();
  const [token, setToken] = useState(searchParams.get("token") ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(nextToken: string) {
    setError(null);
    setSubmitting(true);
    try {
      await verifyEmail(nextToken);
      await refresh();
      setDone(true);
    } catch (caught) {
      setError(formatAuthError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submit(token);
  }

  return (
    <section className="max-w-md">
      <h1 className="font-display text-3xl">Confirm email</h1>
      <p className="mt-2 text-ink-soft">
        {import.meta.env.DEV
          ? "In development, paste the token from the account page outbox if SMTP is not configured."
          : "Use the link from your PaceLab confirmation email, or paste the token here."}
      </p>
      {done ? (
        <p className="mt-8 rounded-sm border border-rule bg-paper-2 px-4 py-3" role="status">
          Email confirmed.{" "}
          <Link to="/settings/account" className="underline">
            Back to account
          </Link>
        </p>
      ) : (
        <form className="mt-8 flex flex-col gap-5" onSubmit={(event) => void onSubmit(event)}>
          <FormError message={error} />
          <Field
            label="Verification token"
            name="token"
            required
            value={token}
            onChange={(event) => setToken(event.target.value)}
          />
          <PrimaryButton disabled={submitting}>
            {submitting ? "Confirming…" : "Confirm email"}
          </PrimaryButton>
        </form>
      )}
    </section>
  );
}
