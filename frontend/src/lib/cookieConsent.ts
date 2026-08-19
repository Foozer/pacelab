const STORAGE_KEY = "pacelab.cookieConsent";

export type CookieConsent = {
  analytics: boolean;
  marketing: boolean;
  updatedAt: string;
};

export function defaultCookieConsent(): CookieConsent {
  return { analytics: false, marketing: false, updatedAt: "" };
}

export function readCookieConsent(): CookieConsent | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as {
      analytics?: unknown;
      marketing?: unknown;
      updatedAt?: unknown;
    };
    return {
      analytics: parsed.analytics === true,
      marketing: parsed.marketing === true,
      updatedAt: typeof parsed.updatedAt === "string" ? parsed.updatedAt : "",
    };
  } catch {
    return null;
  }
}

export function storeCookieConsent(consent: Omit<CookieConsent, "updatedAt">): CookieConsent {
  const next: CookieConsent = {
    analytics: consent.analytics === true,
    marketing: consent.marketing === true,
    updatedAt: new Date().toISOString(),
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return next;
}
