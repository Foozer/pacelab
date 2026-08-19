import { LegalDraftBanner } from "@/components/LegalDraftBanner";

export function TermsOfServicePage() {
  return (
    <article className="flex flex-col gap-6">
      <h1 className="font-display text-3xl">Terms of service</h1>
      <LegalDraftBanner />
      <p className="leading-relaxed text-ink-soft">
        PaceLab is a personal running analytics application. Figures such as aerobic
        efficiency and the 5K estimate are application estimates, not medical advice and
        not a race prediction.
      </p>
      <p className="leading-relaxed text-ink-soft">
        You must not submit a Garmin password to PaceLab. Garmin data, when live import
        exists, will come through official OAuth only.
      </p>
      <p className="leading-relaxed text-ink-soft">
        These terms are a placeholder until they are reviewed. Do not treat this page as a
        binding customer contract.
      </p>
    </article>
  );
}
