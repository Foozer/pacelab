import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ActivitySampleCharts } from "@/components/charts/RunCharts";
import { FormError } from "@/components/Form";
import { ApiError, fetchActivity, formatAuthError } from "@/lib/api";
import { formatDateTime, formatDistance, formatDuration, formatPace } from "@/lib/format";
import type { ActivityDetail } from "@/types/activity";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; activity: ActivityDetail }
  | { status: "error"; message: string };

export function ActivityDetailPage() {
  const { activityId } = useParams();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!activityId) {
      setState({ status: "error", message: "Activity not found" });
      return;
    }
    let cancelled = false;
    setState({ status: "loading" });
    fetchActivity(activityId)
      .then((activity) => {
        if (!cancelled) {
          setState({ status: "ready", activity });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message =
            error instanceof ApiError && error.status === 404
              ? "Activity not found"
              : formatAuthError(error);
          setState({ status: "error", message });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activityId]);

  if (state.status === "loading") {
    return (
      <p className="rounded-sm border border-rule bg-paper-2 px-4 py-3" role="status">
        Loading this run…
      </p>
    );
  }

  if (state.status === "error") {
    return (
      <div>
        <FormError message={state.message} />
        <p className="mt-4 text-sm">
          <Link to="/activities" className="text-moss-deep underline">
            Back to activities
          </Link>
        </p>
      </div>
    );
  }

  const { activity } = state;

  return (
    <article className="flex flex-col gap-10">
      <div>
        <p className="text-sm">
          <Link to="/activities" className="text-moss-deep underline">
            Activities
          </Link>
        </p>
        <h1 className="font-display mt-3 text-3xl">{formatDateTime(activity.started_at)}</h1>
        <p className="mt-2 capitalize text-ink-soft">{activity.activity_type ?? "Run"}</p>
      </div>

      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Distance" value={formatDistance(activity.distance_meters)} />
        <Stat label="Duration" value={formatDuration(activity.duration_seconds)} />
        <Stat label="Average pace" value={formatPace(activity)} />
        <Stat
          label="Average HR"
          value={activity.average_heart_rate != null ? `${activity.average_heart_rate} bpm` : "—"}
        />
        <Stat
          label="Maximum HR"
          value={activity.max_heart_rate != null ? `${activity.max_heart_rate} bpm` : "—"}
        />
        <Stat
          label="Cadence"
          value={
            activity.average_cadence != null ? `${Math.round(activity.average_cadence)} spm` : "—"
          }
        />
        <Stat
          label="Elevation gain"
          value={
            activity.elevation_gain != null ? `${Math.round(activity.elevation_gain)} m` : "—"
          }
        />
      </dl>

      <ActivitySampleCharts samples={activity.samples} />
    </article>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-rule bg-paper-2 px-4 py-4">
      <dt className="text-xs tracking-wide text-ink-soft uppercase">{label}</dt>
      <dd className="font-display mt-2 text-xl">{value}</dd>
    </div>
  );
}
