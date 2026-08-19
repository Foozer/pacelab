import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { DashboardTrendChart } from "@/components/charts/RunCharts";
import { FormError } from "@/components/Form";
import { fetchDashboard, formatAuthError } from "@/lib/api";
import { formatDateTime, formatDistance, formatDuration, formatPace, formatPaceSeconds } from "@/lib/format";
import { readStoredHeartRateRange } from "@/lib/hrRange";
import type {
  AerobicEfficiencyMetric,
  DashboardResponse,
  EasyPaceMetric,
  FiveKEstimateMetric,
} from "@/types/activity";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: DashboardResponse }
  | { status: "error"; message: string };

export function DashboardPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    const range = readStoredHeartRateRange();
    fetchDashboard(range.min, range.max)
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
          Recent volume, last runs, and whether easy pace at a similar heart rate is moving.
          Figures are application estimates, not medical measurements or race predictions.
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
        <EasyPaceCard metric={data.easy_pace} />
        <FiveKCard metric={data.five_k_estimate} />
        <AerobicCard metric={data.aerobic_efficiency} />
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

function EasyPaceCard({ metric }: { metric: EasyPaceMetric }) {
  return (
    <article className="border border-rule bg-paper-2 px-4 py-4">
      <h2 className="text-xs tracking-wide text-ink-soft uppercase">Easy pace</h2>
      {metric.available ? (
        <>
          <p className="font-display mt-3 text-2xl">{formatPaceSeconds(metric.pace_seconds_per_km)}</p>
          <p className="mt-2 text-sm text-ink">{metric.headline}</p>
          <p className="mt-2 text-sm text-ink-soft">
            From {metric.run_count} runs around {metric.heart_rate_min}–{metric.heart_rate_max} bpm.{" "}
            <Link to="/easy-running" className="text-moss-deep underline">
              Easy running
            </Link>
          </p>
        </>
      ) : (
        <>
          <p className="font-display mt-3 text-2xl">{metric.headline}</p>
          <p className="mt-2 text-sm text-ink-soft">{metric.note}</p>
        </>
      )}
    </article>
  );
}

function FiveKCard({ metric }: { metric: FiveKEstimateMetric }) {
  return (
    <article className="border border-rule bg-paper-2 px-4 py-4">
      <h2 className="text-xs tracking-wide text-ink-soft uppercase">5K estimate</h2>
      {metric.available ? (
        <>
          <p className="font-display mt-3 text-3xl">{formatDuration(metric.estimated_seconds)}</p>
          <p className="mt-2 text-sm text-ink">{metric.headline}</p>
          <p className="mt-2 text-sm text-ink-soft">{metric.note}</p>
        </>
      ) : (
        <>
          <p className="font-display mt-3 text-2xl">{metric.headline}</p>
          <p className="mt-2 text-sm text-ink-soft">{metric.note}</p>
        </>
      )}
    </article>
  );
}

function AerobicCard({ metric }: { metric: AerobicEfficiencyMetric }) {
  return (
    <article className="border border-rule bg-paper-2 px-4 py-4">
      <h2 className="text-xs tracking-wide text-ink-soft uppercase">Aerobic efficiency</h2>
      {metric.available ? (
        <>
          <p className="font-display mt-3 text-2xl">{metric.direction_label}</p>
          <p className="mt-2 text-sm text-ink">{metric.headline}</p>
          <p className="mt-2 text-sm text-ink-soft">{metric.note}</p>
        </>
      ) : (
        <>
          <p className="font-display mt-3 text-2xl">{metric.headline}</p>
          <p className="mt-2 text-sm text-ink-soft">{metric.note}</p>
        </>
      )}
    </article>
  );
}
