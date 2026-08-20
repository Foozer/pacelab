import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { CookieConsentControls } from "@/components/CookieConsentControls";
import { Field, FormError, PrimaryButton } from "@/components/Form";
import { useAuth } from "@/features/auth/AuthContext";
import {
  deleteAccount,
  deleteRunningData,
  downloadMyData,
  formatAuthError,
} from "@/lib/api";

export function PrivacyPage() {
  const { clearLocalSession } = useAuth();
  const navigate = useNavigate();
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const [runningPassword, setRunningPassword] = useState("");
  const [runningError, setRunningError] = useState<string | null>(null);
  const [runningStatus, setRunningStatus] = useState<string | null>(null);
  const [accountPassword, setAccountPassword] = useState("");
  const [accountConfirm, setAccountConfirm] = useState("");
  const [accountError, setAccountError] = useState<string | null>(null);

  async function onExport() {
    setExportError(null);
    setExportStatus(null);
    try {
      await downloadMyData();
      setExportStatus(
        "Download started. This file is a copy of what PaceLab stores, not a Strava export.",
      );
    } catch (caught) {
      setExportError(formatAuthError(caught));
    }
  }

  async function onDeleteRunning(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRunningError(null);
    setRunningStatus(null);
    try {
      const result = await deleteRunningData(runningPassword);
      setRunningPassword("");
      setRunningStatus(result.message);
    } catch (caught) {
      setRunningError(formatAuthError(caught));
    }
  }

  async function onDeleteAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAccountError(null);
    if (accountConfirm !== "DELETE") {
      setAccountError('Type DELETE to confirm. This cannot be undone.');
      return;
    }
    try {
      await deleteAccount(accountPassword);
      clearLocalSession();
      navigate("/", { replace: true });
    } catch (caught) {
      setAccountError(formatAuthError(caught));
    }
  }

  return (
    <section className="flex flex-col gap-10">
      <div>
        <h1 className="font-display text-3xl">Privacy</h1>
        <p className="mt-4 leading-relaxed text-ink-soft">
          Running data is personal. Download a copy of your PaceLab data, delete your runs
          while keeping the account, or delete the account entirely.
        </p>
        <p className="mt-3 text-sm text-ink-soft">
          <Link to="/privacy" className="underline">
            Privacy policy (draft)
          </Link>
          {" · "}
          <Link to="/cookies" className="underline">
            Cookie policy (draft)
          </Link>
          {" · "}
          <Link to="/terms" className="underline">
            Terms (draft)
          </Link>
        </p>
      </div>

      <div>
        <h2 className="font-display text-2xl">Download a copy of your PaceLab data</h2>
        <p className="mt-2 text-ink-soft">
          Includes your account email, activities, samples (no GPS is stored), and provider
          sync timestamps. It does not include passwords, session secrets, or a Strava export.
        </p>
        <FormError message={exportError} />
        {exportStatus ? (
          <p className="mt-3 text-sm text-moss-deep" role="status">
            {exportStatus}
          </p>
        ) : null}
        <button
          type="button"
          className="mt-4 bg-moss-deep px-4 py-2 text-paper hover:bg-moss"
          onClick={() => {
            void onExport();
          }}
        >
          Download my data
        </button>
      </div>

      <form className="flex max-w-md flex-col gap-4" onSubmit={(event) => void onDeleteRunning(event)}>
        <h2 className="font-display text-2xl">Delete my running data</h2>
        <p className="text-ink-soft">
          Removes your activities, samples, and provider sync records. Your account stays.
          This cannot be undone. Dashboard and analytics will show the empty states.
        </p>
        <FormError message={runningError} />
        {runningStatus ? (
          <p className="text-sm text-moss-deep" role="status">
            {runningStatus}
          </p>
        ) : null}
        <Field
          label="Current password"
          name="running_password"
          type="password"
          autoComplete="current-password"
          required
          value={runningPassword}
          onChange={(event) => setRunningPassword(event.target.value)}
        />
        <PrimaryButton>Delete running data</PrimaryButton>
      </form>

      <form className="flex max-w-md flex-col gap-4" onSubmit={(event) => void onDeleteAccount(event)}>
        <h2 className="font-display text-2xl">Delete my account</h2>
        <p className="text-ink-soft">
          Permanently removes your PaceLab account and the data attached to it. This cannot
          be undone.
        </p>
        <FormError message={accountError} />
        <Field
          label='Type DELETE to confirm'
          name="account_confirm"
          required
          value={accountConfirm}
          onChange={(event) => setAccountConfirm(event.target.value)}
        />
        <Field
          label="Current password"
          name="account_password"
          type="password"
          autoComplete="current-password"
          required
          value={accountPassword}
          onChange={(event) => setAccountPassword(event.target.value)}
        />
        <button type="submit" className="bg-copper px-4 py-2 text-paper hover:opacity-90">
          Delete my account
        </button>
      </form>

      <div>
        <h2 className="font-display text-2xl">Cookies</h2>
        <p className="mt-2 mb-4 text-ink-soft">
          Necessary session cookies cannot be turned off. Optional categories default to off
          and do not enable a tracker.
        </p>
        <CookieConsentControls />
      </div>
    </section>
  );
}
