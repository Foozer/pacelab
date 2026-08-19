import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { DashboardTrendChart } from "@/components/charts/RunCharts";
import { FormError } from "@/components/Form";
import { fetchDashboard, formatAuthError } from "@/lib/api";
import { formatDateTime, formatDistance, formatDuration, formatPace } from "@/lib/format";
import type { DashboardResponse, UpcomingMetric } from "@/types/activity";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: DashboardResponse }
  | { status: "error"; message: string };

export function DashboardPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchDashboard()
      .then((data) => {
        if (!cancelled) {
          setState({ status: "ready", data });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({ status: "error", message: formatAuthError(error) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.status === "loading") {
    return (
      <p className="rounded-sm border border-rule bg-paper-2 px-4 py-3" role="status">
        Loading your running…
      </p>
    );
  }

  if (state.status === "error") {
    return <FormError message={state.message} />;
  }

  const { data } = state;
  const empty = data.recent_activities.length === 0;

  return (
    <section className="flex flex-col gap-10">
      <div>
        <h1 className="font-display text-3xl">How is my running going?</h1>
        <p className="mt-3 max-w-2xl text-ink-soft">
          A quiet view of recent volume, your last runs, and pace versus heart rate. Fitness
          estimates come later — nothing here is a medical measurement.
        </p>
      </div>

      {empty ? (
        <p className="rounded-sm border border-rule bg-paper-2 px-4 py-3">
          No runs yet.{" "}
          <Link to="/activities" className="text-moss-deep underline">
            Import mock runs
          </Link>{" "}
          to fill this page, or ask someone with access to run the seed command.
        </p>
      ) : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <WeeklyCard weekly={data.weekly} />
        <PlaceholderCard metric={data.easy_pace} />
        <PlaceholderCard metric={data.five_k_estimate} />
        <PlaceholderCard metric={data.aerobic_efficiency} />
      </div>

      <section aria-labelledby="recent-runs">
        <h2 id="recent-runs" className="font-display text-2xl">
          Recent runs
        </h2>
        {data.recent_activities.length === 0 ? (
          <p className="mt-3 text-ink-soft">Nothing to show yet.</p>
        ) : (
          <ul className="mt-4 divide-y divide-rule">
            {data.recent_activities.map((activity) => (
              <li key={activity.id} className="py-3">
                <Link to={`/activities/${activity.id}`} className="flex flex-wrap justify-between gap-2">
                  <span>{formatDateTime(activity.started_at)}</span>
                  <span className="text-ink-soft">
                    {formatDistance(activity.distance_meters)} · {formatDuration(activity.duration_seconds)}{" "}
                    · {formatPace(activity)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 text-sm">
          <Link to="/activities" className="text-moss-deep underline">
            All activities
          </Link>
        </p>
      </section>

      <section aria-labelledby="recent-trend">
        <h2 id="recent-trend" className="font-display text-2xl">
          Pace and heart rate
        </h2>
        <p className="mt-2 text-sm text-ink-soft">
          Average pace (moss) and average heart rate (copper) across your recent runs. Faster pace
          sits toward the top.
        </p>
        <DashboardTrendChart points={data.pace_heart_rate_trend} />
      </section>
    </section>
  );
}

function WeeklyCard({ weekly }: { weekly: DashboardResponse["weekly"] }) {
  return (
    <article className="border border-rule bg-paper-2 px-4 py-4 sm:col-span-2 lg:col-span-1">
      <h2 className="text-xs tracking-wide text-ink-soft uppercase">Last 7 days</h2>
      <p className="font-display mt-3 text-3xl">{weekly.run_count} runs</p>
      <p className="mt-2 text-ink">
        {formatDistance(weekly.distance_meters)} · {formatDuration(weekly.duration_seconds)}
      </p>
    </article>
  );
}

function PlaceholderCard({ metric }: { metric: UpcomingMetric }) {
  return (
    <article className="border border-dashed border-rule px-4 py-4">
      <h2 className="text-xs tracking-wide text-ink-soft uppercase">{metric.label}</h2>
      <p className="font-display mt-3 text-2xl text-ink-soft">Not calculated yet</p>
      <p className="mt-2 text-sm text-ink-soft">{metric.note}</p>
    </article>
  );
}
