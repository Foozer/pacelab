import { Link } from "react-router-dom";

import { LegalDraftBanner } from "@/components/LegalDraftBanner";

export function PrivacyPolicyPage() {
  return (
    <article className="flex flex-col gap-6">
      <h1 className="font-display text-3xl">Privacy policy</h1>
      <LegalDraftBanner />
      <p className="leading-relaxed text-ink-soft">
        PaceLab stores an account (email and a password hash), running activities, and
        activity samples used for pace and heart-rate analysis. Samples do not include GPS
        coordinates. Session cookies identify a signed-in browser. Provider sync records
        store a provider name and last sync time only.
      </p>
      <p className="leading-relaxed text-ink-soft">
        You can import runs as FIT files or connect Strava with official OAuth. PaceLab does not
        collect Strava passwords and does not scrape Strava. Encrypted Strava tokens, when you
        connect, are stored only for syncing your activities.
      </p>
      <p className="leading-relaxed text-ink-soft">
        You can download a copy of the data PaceLab stores, delete running data while
        keeping the account, or delete the account. Analytics figures are application
        estimates, not medical advice.
      </p>
      <p className="text-sm text-ink-soft">
        Signed-in controls live under{" "}
        <Link to="/settings/privacy" className="underline">
          Settings → Privacy
        </Link>
        .
      </p>
    </article>
  );
}
