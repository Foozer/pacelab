import { useCallback, useEffect, useState } from "react";

import { FormError, PrimaryButton } from "@/components/Form";
import { fetchActivities, formatAuthError, syncActivities } from "@/lib/api";
import type { ActivityListResponse, ActivitySummary } from "@/types/activity";

const PAGE_SIZE = 20;

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: ActivityListResponse }
  | { status: "error"; message: string };

export function ActivitiesPage() {
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [syncing, setSyncing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async (nextOffset: number) => {
    setState({ status: "loading" });
    try {
      const data = await fetchActivities(PAGE_SIZE, nextOffset);
      setState({ status: "ready", data });
    } catch (error) {
      setState({ status: "error", message: formatAuthError(error) });
    }
  }, []);

  useEffect(() => {
    void load(offset);
  }, [load, offset]);

  async function onSync() {
    setSyncing(true);
    setNotice(null);
    try {
      const result = await syncActivities();
      setNotice(
        `Imported ${result.created} new, updated ${result.updated}. ${result.total} activities from ${result.provider}.`,
      );
      setOffset(0);
      await load(0);
    } catch (error) {
      setNotice(formatAuthError(error));
    } finally {
      setSyncing(false);
    }
  }

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl">Activities</h1>
          <p className="mt-3 max-w-xl text-ink-soft">
            Your imported runs. Charts and trends arrive in a later phase. Use mock import until
            official Garmin OAuth is available.
          </p>
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void onSync();
          }}
        >
          <PrimaryButton disabled={syncing}>
            {syncing ? "Importing…" : "Import mock runs"}
          </PrimaryButton>
        </form>
      </div>

      {notice ? <p className="mt-6 text-sm text-ink-soft">{notice}</p> : null}

      {state.status === "loading" ? (
        <p className="mt-8 rounded-sm border border-rule bg-paper-2 px-4 py-3" role="status">
          Loading activities…
        </p>
      ) : null}

      {state.status === "error" ? (
        <div className="mt-8">
          <FormError message={state.message} />
        </div>
      ) : null}

      {state.status === "ready" ? <ActivityTable data={state.data} offset={offset} onPage={setOffset} /> : null}
    </section>
  );
}

function ActivityTable({
  data,
  offset,
  onPage,
}: {
  data: ActivityListResponse;
  offset: number;
  onPage: (offset: number) => void;
}) {
  if (data.total === 0) {
    return (
      <p className="mt-8 rounded-sm border border-rule bg-paper-2 px-4 py-3">
        No activities yet. Import mock runs, or run{" "}
        <code className="font-mono text-sm">python -m app.db.seed</code> from the backend
        directory.
      </p>
    );
  }

  const page = Math.floor(offset / data.limit) + 1;
  const pageCount = Math.max(1, Math.ceil(data.total / data.limit));

  return (
    <>
      <p className="mt-8 text-sm text-ink-soft">
        {data.total} runs
        {data.last_sync_at ? ` · last import ${formatDateTime(data.last_sync_at)}` : ""}
      </p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-rule text-ink-soft">
              <th className="py-2 pr-4 font-normal">Date</th>
              <th className="py-2 pr-4 font-normal">Distance</th>
              <th className="py-2 pr-4 font-normal">Duration</th>
              <th className="py-2 pr-4 font-normal">Pace</th>
              <th className="py-2 pr-4 font-normal">Average HR</th>
              <th className="py-2 font-normal">Type</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((activity) => (
              <tr key={activity.id} className="border-b border-rule/70">
                <td className="py-3 pr-4">{formatDateTime(activity.started_at)}</td>
                <td className="py-3 pr-4">{formatDistance(activity.distance_meters)}</td>
                <td className="py-3 pr-4">{formatDuration(activity.duration_seconds)}</td>
                <td className="py-3 pr-4">{formatPace(activity)}</td>
                <td className="py-3 pr-4">
                  {activity.average_heart_rate != null ? `${activity.average_heart_rate} bpm` : "—"}
                </td>
                <td className="py-3 capitalize">{activity.activity_type ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-6 flex items-center justify-between text-sm">
        <p className="text-ink-soft">
          Page {page} of {pageCount}
        </p>
        <div className="flex gap-3">
          <button
            type="button"
            className="text-moss-deep disabled:text-ink-soft"
            disabled={offset <= 0}
            onClick={() => onPage(Math.max(0, offset - data.limit))}
          >
            Previous
          </button>
          <button
            type="button"
            className="text-moss-deep disabled:text-ink-soft"
            disabled={offset + data.limit >= data.total}
            onClick={() => onPage(offset + data.limit)}
          >
            Next
          </button>
        </div>
      </div>
    </>
  );
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function formatDistance(meters: number | null): string {
  if (meters == null) {
    return "—";
  }
  return `${(meters / 1000).toFixed(2)} km`;
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) {
    return "—";
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = seconds % 60;
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
  }
  return `${minutes}:${String(remainder).padStart(2, "0")}`;
}

function formatPace(activity: ActivitySummary): string {
  if (activity.distance_meters == null || activity.duration_seconds == null) {
    return "—";
  }
  if (activity.distance_meters < 1 || activity.duration_seconds < 1) {
    return "—";
  }
  const secondsPerKm = activity.duration_seconds / (activity.distance_meters / 1000);
  const minutes = Math.floor(secondsPerKm / 60);
  const seconds = Math.round(secondsPerKm % 60);
  return `${minutes}:${String(seconds).padStart(2, "0")}/km`;
}
