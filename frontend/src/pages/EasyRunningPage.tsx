import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { EasyPaceTrendChart } from "@/components/charts/RunCharts";
import { FormError } from "@/components/Form";
import { HeartRateRangeForm } from "@/components/HeartRateRangeForm";
import { fetchEasyRunning, formatAuthError } from "@/lib/api";
import { formatDistance, formatPaceSeconds } from "@/lib/format";
import {
  type HeartRateRange,
  readStoredHeartRateRange,
  storeHeartRateRange,
} from "@/lib/hrRange";
import type { EasyRunningResponse } from "@/types/activity";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: EasyRunningResponse }
  | { status: "error"; message: string };

export function EasyRunningPage() {
  const [range, setRange] = useState<HeartRateRange>(readStoredHeartRateRange);
  const [draft, setDraft] = useState<HeartRateRange>(range);
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    fetchEasyRunning(range.min, range.max)
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
  }, [range]);

  function applyRange(event: FormEvent) {
    event.preventDefault();
    if (draft.min >= draft.max) {
      setState({ status: "error", message: "The lower heart rate must be below the upper one." });
      return;
    }
    storeHeartRateRange(draft);
    setRange(draft);
  }

  return (
    <section className="flex flex-col gap-8">
      <div>
        <h1 className="font-display text-3xl">Easy running</h1>
        <p className="mt-3 max-w-2xl text-ink-soft">
          Pace on runs in a heart-rate range you choose. The default 140–150 bpm is a starting
          point, not a personal Zone 2. Nothing here is a medical measurement.
        </p>
      </div>

      <form onSubmit={applyRange} className="border border-rule bg-paper-2 px-4 py-4">
        <HeartRateRangeForm
          range={draft}
          onChange={setDraft}
          hint="Saved in this browser only. You can also change it under Settings."
        />
        <button type="submit" className="mt-4 bg-moss-deep px-4 py-2 text-paper hover:bg-moss">
          Update range
        </button>
      </form>

      {state.status === "loading" ? (
        <p className="rounded-sm border border-rule bg-paper-2 px-4 py-3" role="status">
          Loading easy runs…
        </p>
      ) : null}
      {state.status === "error" ? <FormError message={state.message} /> : null}
      {state.status === "ready" ? <EasyRunningBody data={state.data} /> : null}
    </section>
  );
}

function EasyRunningBody({ data }: { data: EasyRunningResponse }) {
  return (
    <>
      <p className="font-display text-2xl">{data.headline}</p>
      <p className="text-sm text-ink-soft">{data.note}</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Average pace" value={formatPaceSeconds(data.average_pace_seconds_per_km)} />
        <Stat label="Runs" value={String(data.run_count)} />
        <Stat label="Distance" value={formatDistance(data.distance_meters)} />
        <Stat
          label="Average HR"
          value={data.average_heart_rate == null ? "—" : `${Math.round(data.average_heart_rate)} bpm`}
        />
      </div>
      <p className="text-sm text-ink-soft">
        Pace at a comparable heart rate (mid-range):{" "}
        {formatPaceSeconds(data.comparable_pace_seconds_per_km)}
      </p>
      <section aria-labelledby="easy-trend">
        <h2 id="easy-trend" className="font-display text-2xl">
          Pace trend
        </h2>
        <p className="mt-2 text-sm text-ink-soft">
          Faster sits toward the top. Points are scaled to the middle of your chosen range so
          runs at 142 and 149 bpm can be compared.
        </p>
        <EasyPaceTrendChart points={data.points} />
      </section>
      <p className="text-sm">
        <Link to="/trends" className="text-moss-deep underline">
          Longer-term trends
        </Link>
      </p>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <article className="border border-rule bg-paper-2 px-4 py-4">
      <h2 className="text-xs tracking-wide text-ink-soft uppercase">{label}</h2>
      <p className="font-display mt-3 text-2xl">{value}</p>
    </article>
  );
}
