import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Field, FormError, PrimaryButton } from "@/components/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { changePassword, fetchDevOutbox, formatAuthError, resendVerification } from "@/lib/api";
import type { DevOutboxItem } from "@/types/auth";

export function AccountPage() {
  const { user, refresh } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [verifyMessage, setVerifyMessage] = useState<string | null>(null);
  const [outbox, setOutbox] = useState<DevOutboxItem[] | null>(null);

  useEffect(() => {
    if (import.meta.env.PROD) {
      return;
    }
    let cancelled = false;
    fetchDevOutbox()
      .then((result) => {
        if (!cancelled) {
          setOutbox(result?.emails ?? null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setOutbox(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [user?.email_verified, verifyMessage, passwordMessage]);

  if (!user) {
    return null;
  }

  async function onChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError(null);
    setPasswordMessage(null);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setPasswordMessage("Password updated.");
      await refresh();
    } catch (caught) {
      setPasswordError(formatAuthError(caught));
    }
  }

  async function onResend() {
    setVerifyMessage(null);
    try {
      const result = await resendVerification();
      setVerifyMessage(result.message);
      if (!import.meta.env.PROD) {
        const latest = await fetchDevOutbox();
        setOutbox(latest?.emails ?? null);
      }
    } catch (caught) {
      setVerifyMessage(formatAuthError(caught));
    }
  }

  return (
    <section className="flex flex-col gap-10">
      <div>
        <h1 className="font-display text-3xl">Account</h1>
        <p className="mt-2 text-ink-soft">Signed in as {user.email}.</p>
        <p className="mt-3 text-sm text-ink-soft">
          <Link to="/settings/privacy" className="underline">
            Privacy
          </Link>
          : download your data, delete running data, or delete this account.
        </p>
      </div>

      <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="border border-rule bg-paper-2 px-4 py-4">
          <dt className="text-xs tracking-wide text-ink-soft uppercase">Email</dt>
          <dd className="mt-2">{user.email}</dd>
        </div>
        <div className="border border-rule bg-paper-2 px-4 py-4">
          <dt className="text-xs tracking-wide text-ink-soft uppercase">Email status</dt>
          <dd className="mt-2">{user.email_verified ? "Confirmed" : "Not confirmed yet"}</dd>
        </div>
      </dl>

      {!user.email_verified ? (
        <div>
          <h2 className="font-display text-2xl">Confirm your email</h2>
          <p className="mt-2 text-ink-soft">
            Confirmation is optional for now, but the flow is in place for later.
          </p>
          <button
            type="button"
            onClick={() => {
              void onResend();
            }}
            className="mt-4 text-moss-deep underline"
          >
            Resend confirmation
          </button>
          {verifyMessage ? <p className="mt-3 text-sm text-ink-soft">{verifyMessage}</p> : null}
          <p className="mt-3 text-sm text-ink-soft">
            Have a token?{" "}
            <Link to="/verify-email" className="underline">
              Confirm email
            </Link>
          </p>
        </div>
      ) : null}

      <form className="max-w-md flex flex-col gap-5" onSubmit={(event) => void onChangePassword(event)}>
        <h2 className="font-display text-2xl">Change password</h2>
        <FormError message={passwordError} />
        {passwordMessage ? (
          <p className="rounded-sm border border-rule bg-paper-2 px-4 py-3" role="status">
            {passwordMessage}
          </p>
        ) : null}
        <Field
          label="Current password"
          name="current_password"
          type="password"
          autoComplete="current-password"
          required
          value={currentPassword}
          onChange={(event) => setCurrentPassword(event.target.value)}
        />
        <Field
          label="New password"
          name="new_password"
          type="password"
          autoComplete="new-password"
          minLength={10}
          required
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
        />
        <PrimaryButton>Update password</PrimaryButton>
      </form>

      {outbox && outbox.length > 0 ? (
        <div>
          <h2 className="font-display text-2xl">Development mailbox</h2>
          <p className="mt-2 text-sm text-ink-soft">
            Visible only while ENVIRONMENT=development. Tokens are not written to application logs.
          </p>
          <ul className="mt-4 flex flex-col gap-3">
            {outbox.map((item) => (
              <li key={`${item.template}-${item.subject}`} className="border border-rule bg-paper-2 px-4 py-3">
                <p className="text-sm text-ink-soft">{item.template}</p>
                <p className="mt-1 font-medium">{item.subject}</p>
                <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-sm">{item.body}</pre>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
