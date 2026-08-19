import { Link } from "react-router-dom";

import { CookieConsentControls } from "@/components/CookieConsentControls";
import { LegalDraftBanner } from "@/components/LegalDraftBanner";

export function CookiePolicyPage() {
  return (
    <article className="flex flex-col gap-6">
      <h1 className="font-display text-3xl">Cookie policy</h1>
      <LegalDraftBanner />
      <p className="leading-relaxed text-ink-soft">
        PaceLab currently sets two necessary cookies when you use the app:
      </p>
      <ul className="list-disc space-y-2 pl-5 text-ink-soft">
        <li>
          <code>pacelab_session</code> — HttpOnly session cookie so the API knows who you
          are.
        </li>
        <li>
          <code>pacelab_csrf</code> — readable cookie used with the <code>X-CSRF-Token</code>{" "}
          header to protect sign-in and other form posts.
        </li>
      </ul>
      <p className="leading-relaxed text-ink-soft">
        Analytics and marketing categories are listed so a later release can ask before
        enabling them. They default to off. PaceLab does not load Google Analytics or any
        other tracker. Saving an optional choice is stored in this browser only
        (localStorage), not as a tracking cookie.
      </p>
      <CookieConsentControls />
      <p className="text-sm text-ink-soft">
        See also the{" "}
        <Link to="/privacy" className="underline">
          privacy policy draft
        </Link>
        .
      </p>
    </article>
  );
}
