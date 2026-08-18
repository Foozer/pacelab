import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { Field, FormError, PrimaryButton } from "@/components/Form";
import { formatAuthError } from "@/lib/api";
import { requestPasswordReset } from "@/lib/api";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setSubmitting(true);
    try {
      const result = await requestPasswordReset(email);
      setMessage(result.message);
    } catch (caught) {
      setError(formatAuthError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="max-w-md">
      <h1 className="font-display text-3xl">Reset password</h1>
      <p className="mt-2 text-ink-soft">
        If an account exists for that email, PaceLab queues a reset message. Email delivery is not
        configured yet; in local development the token appears on the account page.
      </p>
      <form className="mt-8 flex flex-col gap-5" onSubmit={(event) => void onSubmit(event)}>
        <FormError message={error} />
        {message ? (
          <p className="rounded-sm border border-rule bg-paper-2 px-4 py-3" role="status">
            {message}
          </p>
        ) : null}
        <Field
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <PrimaryButton disabled={submitting}>{submitting ? "Sending…" : "Send reset link"}</PrimaryButton>
      </form>
      <p className="mt-6 text-sm text-ink-soft">
        <Link to="/login" className="underline">
          Back to log in
        </Link>
      </p>
    </section>
  );
}
