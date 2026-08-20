import { Link } from "react-router-dom";

import { useAuth } from "@/features/auth/AuthContext";
import { DashboardPage } from "@/pages/DashboardPage";

export function HomePage() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <p className="rounded-sm border border-rule bg-paper-2 px-4 py-3" role="status">
        Checking your session…
      </p>
    );
  }

  if (user) {
    return <DashboardPage />;
  }

  return <LandingPage />;
}

function LandingPage() {
  return (
    <div className="flex flex-col gap-16 pb-6">
      <section className="landing-reveal max-w-2xl">
        <p className="text-sm tracking-[0.18em] text-ink-soft uppercase">Private friends beta</p>
        <h1 className="font-display mt-4 text-4xl leading-tight sm:text-5xl">
          How is my running going?
        </h1>
        <p className="mt-5 text-lg leading-relaxed text-ink-soft">
          PaceLab helps you see whether fitness is actually improving — pace relative to heart
          rate, easy running, and long-term trends. Bring runs in as FIT files or from Strava.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Link
            to="/register"
            className="bg-moss-deep px-5 py-2.5 text-paper transition-colors hover:bg-moss"
          >
            Create an account
          </Link>
          <Link to="/login" className="text-moss-deep underline underline-offset-4">
            Log in
          </Link>
        </div>
      </section>

      <section className="landing-reveal landing-reveal-delay-1" aria-labelledby="answers">
        <h2 id="answers" className="font-display text-2xl">
          Answers runners actually need
        </h2>
        <p className="mt-3 max-w-2xl text-ink-soft">
          After you import runs, the home dashboard and analytics pages focus on progress — not
          maps, badges, or social feeds.
        </p>
        <ul className="mt-8 divide-y divide-rule border-y border-rule">
          <FeatureRow
            title="Aerobic efficiency"
            body="Whether you are covering ground with less heart-rate cost on easy and moderate runs."
          />
          <FeatureRow
            title="Easy running"
            body="Pace and volume inside a heart-rate band you choose, so easy days stay honest."
          />
          <FeatureRow
            title="Trends"
            body="Pace, heart rate, weekly distance, and frequency over weeks and months."
          />
          <FeatureRow
            title="5K estimate"
            body="A Riegel-based estimate from recent longer runs — useful context, not a race guarantee."
          />
        </ul>
      </section>

      <section className="landing-reveal landing-reveal-delay-2" aria-labelledby="bring-runs">
        <h2 id="bring-runs" className="font-display text-2xl">
          Bring your runs in
        </h2>
        <p className="mt-3 max-w-2xl leading-relaxed text-ink-soft">
          Upload <code className="font-mono text-sm">.fit</code> files from your watch, or connect
          Strava and sync. PaceLab never asks for a Strava password and does not scrape Strava. It
          is not a Strava partner.
        </p>
      </section>

      <section className="landing-reveal landing-reveal-delay-3" aria-labelledby="who-for">
        <h2 id="who-for" className="font-display text-2xl">
          Built for a small circle
        </h2>
        <p className="mt-3 max-w-2xl leading-relaxed text-ink-soft">
          This is a private friends beta on one secure site — real email for verification and
          password reset, your data under your account, export and delete when you want them. Legal
          pages are still drafts. There are no ad trackers.
        </p>
        <p className="mt-8 text-ink">
          Ready to try it?{" "}
          <Link to="/register" className="text-moss-deep underline underline-offset-4">
            Create an account
          </Link>{" "}
          or{" "}
          <Link to="/login" className="text-moss-deep underline underline-offset-4">
            log in
          </Link>
          .
        </p>
      </section>
    </div>
  );
}

function FeatureRow({ title, body }: { title: string; body: string }) {
  return (
    <li className="grid gap-2 py-5 sm:grid-cols-[12rem_1fr] sm:gap-8">
      <h3 className="font-display text-xl text-ink">{title}</h3>
      <p className="leading-relaxed text-ink-soft">{body}</p>
    </li>
  );
}
