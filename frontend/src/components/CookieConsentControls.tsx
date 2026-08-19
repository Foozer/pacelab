import { useState } from "react";

import {
  defaultCookieConsent,
  readCookieConsent,
  storeCookieConsent,
  type CookieConsent,
} from "@/lib/cookieConsent";

export function CookieConsentControls({ onSaved }: { onSaved?: (consent: CookieConsent) => void }) {
  const stored = readCookieConsent();
  const [analytics, setAnalytics] = useState(stored?.analytics ?? false);
  const [marketing, setMarketing] = useState(stored?.marketing ?? false);
  const [status, setStatus] = useState<string | null>(null);

  function save(nextAnalytics: boolean, nextMarketing: boolean) {
    const saved = storeCookieConsent({ analytics: nextAnalytics, marketing: nextMarketing });
    setAnalytics(saved.analytics);
    setMarketing(saved.marketing);
    setStatus(
      "Saved in this browser. PaceLab still does not load analytics or marketing scripts.",
    );
    onSaved?.(saved);
  }

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        save(analytics, marketing);
      }}
    >
      <fieldset className="border border-rule bg-paper-2 px-4 py-4">
        <legend className="px-1 text-sm">Necessary</legend>
        <p className="text-sm text-ink-soft">
          Session cookies <code>pacelab_session</code> (HttpOnly) and{" "}
          <code>pacelab_csrf</code> keep you signed in and protect form posts. They cannot
          be turned off while you use a signed-in session.
        </p>
        <label className="mt-3 flex items-center gap-2 text-sm">
          <input type="checkbox" checked disabled />
          Always on
        </label>
      </fieldset>
      <fieldset className="border border-rule bg-paper-2 px-4 py-4">
        <legend className="px-1 text-sm">Analytics</legend>
        <p className="text-sm text-ink-soft">
          Reserved for a later product decision. There is no analytics tracker today.
          Turning this on does not send data anywhere and does not add a script.
        </p>
        <label className="mt-3 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={analytics}
            onChange={(event) => setAnalytics(event.target.checked)}
          />
          Allow analytics cookies later
        </label>
      </fieldset>
      <fieldset className="border border-rule bg-paper-2 px-4 py-4">
        <legend className="px-1 text-sm">Marketing</legend>
        <p className="text-sm text-ink-soft">
          Reserved for a later product decision. There are no marketing pixels or ads.
          Turning this on does not enable tracking.
        </p>
        <label className="mt-3 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={marketing}
            onChange={(event) => setMarketing(event.target.checked)}
          />
          Allow marketing cookies later
        </label>
      </fieldset>
      <div className="flex flex-wrap gap-3">
        <button type="submit" className="bg-moss-deep px-4 py-2 text-paper hover:bg-moss">
          Save cookie choices
        </button>
        <button
          type="button"
          className="border border-rule px-4 py-2 hover:border-moss"
          onClick={() => {
            const defaults = defaultCookieConsent();
            setAnalytics(defaults.analytics);
            setMarketing(defaults.marketing);
            save(false, false);
          }}
        >
          Necessary only
        </button>
      </div>
      {status ? (
        <p className="text-sm text-moss-deep" role="status">
          {status}
        </p>
      ) : null}
    </form>
  );
}
