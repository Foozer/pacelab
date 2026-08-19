import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { FormError, PrimaryButton } from "@/components/Form";
import { fetchActivities, formatAuthError, importFitFiles, syncActivities } from "@/lib/api";
import { formatDateTime, formatDistance, formatDuration, formatPace } from "@/lib/format";
import type { ActivityListResponse } from "@/types/activity";

const PAGE_SIZE = 20;

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: ActivityListResponse }
  | { status: "error"; message: string };

export function ActivitiesPage() {
  const [offset, setOffset] = useState(0);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [activityType, setActivityType] = useState("");
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [syncing, setSyncing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [fitError, setFitError] = useState<string | null>(null);

  const load = useCallback(
    async (nextOffset: number) => {
      setState({ status: "loading" });
      try {
        const data = await fetchActivities({
          limit: PAGE_SIZE,
          offset: nextOffset,
          fromDate: fromDate || undefined,
          toDate: toDate || undefined,
          activityType: activityType || undefined,
        });
        setState({ status: "ready", data });
      } catch (error) {
        setState({ status: "error", message: formatAuthError(error) });
      }
    },
    [activityType, fromDate, toDate],
  );

  useEffect(() => {
    void load(offset);
  }, [load, offset]);

  async function onSync() {
    setSyncing(true);
    setNotice(null);
    setFitError(null);
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

  async function onFitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = form.elements.namedItem("fit_files");
    if (!(input instanceof HTMLInputElement) || !input.files || input.files.length === 0) {
      setFitError("Choose one or more .fit files.");
      return;
    }
    setUploading(true);
    setNotice(null);
    setFitError(null);
    try {
      const result = await importFitFiles(Array.from(input.files));
      const parts = [
        result.created ? `${result.created} imported` : null,
        result.updated ? `${result.updated} updated` : null,
        result.failed ? `${result.failed} failed` : null,
      ].filter(Boolean);
      setNotice(`FIT upload: ${parts.join(", ") || "no changes"}.`);
      form.reset();
      setOffset(0);
      await load(0);
    } catch (error) {
      setFitError(formatAuthError(error));
    } finally {
      setUploading(false);
    }
  }

  function applyFilters(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    void load(0);
  }

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl">Activities</h1>
          <p className="mt-3 max-w-xl text-ink-soft">
            Your imported runs, one page at a time. Filter by date or type without loading
            everything into the browser.
          </p>
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void onSync();
          }}
        >
          <PrimaryButton disabled={syncing}>
            {syncing ? "Importing…" : "Sync sample runs"}
          </PrimaryButton>
        </form>
      </div>

      <div className="mt-8 border border-rule bg-paper-2 px-4 py-4">
        <h2 className="font-display text-2xl">Upload FIT files</h2>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-soft">
          Import a run from your watch or Garmin Connect by uploading the original{" "}
          <code className="font-mono">.fit</code> file. PaceLab does not log into Garmin and is
          not a live Garmin connection. In Garmin Connect, open an activity and export the original
          file, or copy <code className="font-mono">.fit</code> files from the device activity
          folder.
        </p>
        <form className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={onFitUpload}>
          <label className="block min-w-0 flex-1">
            <span className="text-sm text-ink">FIT files</span>
            <input
              name="fit_files"
              type="file"
              accept=".fit,.fit.gz,application/octet-stream"
              multiple
              className="mt-2 w-full border border-rule bg-paper px-3 py-2 text-ink file:mr-3 file:border-0 file:bg-moss-deep file:px-3 file:py-1 file:text-paper"
            />
          </label>
          <PrimaryButton disabled={uploading}>{uploading ? "Uploading…" : "Upload"}</PrimaryButton>
        </form>
        {fitError ? (
          <div className="mt-4">
            <FormError message={fitError} />
          </div>
        ) : null}
      </div>

      <form
        className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-4 sm:items-end"
        onSubmit={applyFilters}
      >
        <label className="block">
          <span className="text-sm text-ink">From</span>
          <input
            type="date"
            value={fromDate}
            onChange={(event) => {
              setFromDate(event.target.value);
              setOffset(0);
            }}
            className="mt-2 w-full border border-rule bg-paper px-3 py-2 text-ink outline-none focus:border-moss"
          />
        </label>
        <label className="block">
          <span className="text-sm text-ink">To</span>
          <input
            type="date"
            value={toDate}
            onChange={(event) => {
              setToDate(event.target.value);
              setOffset(0);
            }}
            className="mt-2 w-full border border-rule bg-paper px-3 py-2 text-ink outline-none focus:border-moss"
          />
        </label>
        <label className="block">
          <span className="text-sm text-ink">Type</span>
          <select
            value={activityType}
            onChange={(event) => {
              setActivityType(event.target.value);
              setOffset(0);
            }}
            className="mt-2 w-full border border-rule bg-paper px-3 py-2 text-ink outline-none focus:border-moss"
          >
            <option value="">All types</option>
            {(state.status === "ready" ? state.data.activity_types : []).map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="border border-rule px-3 py-2 text-sm text-ink hover:bg-paper-2">
          Apply dates
        </button>
      </form>

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

      {state.status === "ready" ? (
        <ActivityTable data={state.data} offset={offset} onPage={setOffset} />
      ) : null}
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
        No activities match these filters. Upload a FIT file, sync sample runs, or run{" "}
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
        {data.total} {data.total === 1 ? "activity" : "activities"}
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
                <td className="py-3 pr-4">
                  <Link to={`/activities/${activity.id}`} className="text-moss-deep underline">
                    {formatDateTime(activity.started_at)}
                  </Link>
                </td>
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
