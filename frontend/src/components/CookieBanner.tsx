import { useState } from "react";
import { Link } from "react-router-dom";

import { CookieConsentControls } from "@/components/CookieConsentControls";
import { readCookieConsent, storeCookieConsent } from "@/lib/cookieConsent";

export function CookieBanner() {
  const [visible, setVisible] = useState(() => readCookieConsent() === null);

  if (!visible) {
    return null;
  }

  return (
    <div
      className="fixed right-4 bottom-4 left-4 z-40 mx-auto max-w-5xl border border-rule bg-paper px-4 py-4 shadow-sm"
      role="region"
      aria-label="Cookie choices"
    >
      <p className="text-sm leading-relaxed">
        PaceLab uses necessary cookies only: <code>pacelab_session</code> and{" "}
        <code>pacelab_csrf</code>. Analytics and marketing categories exist for later and
        are off. No tracking scripts are loaded.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
        <button
          type="button"
          className="bg-moss-deep px-3 py-2 text-paper hover:bg-moss"
          onClick={() => {
            storeCookieConsent({ analytics: false, marketing: false });
            setVisible(false);
          }}
        >
          Necessary only
        </button>
        <Link to="/cookies" className="text-moss-deep underline">
          Cookie settings
        </Link>
      </div>
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-ink-soft">Choose optional categories</summary>
        <div className="mt-3">
          <CookieConsentControls
            onSaved={() => {
              setVisible(false);
            }}
          />
        </div>
      </details>
    </div>
  );
}
