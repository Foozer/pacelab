import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import {
  ComparablePaceChart,
  HeartRateOverTimeChart,
  PaceOverTimeChart,
  WeeklyDistanceChart,
  WeeklyFrequencyChart,
} from "@/components/charts/RunCharts";
import { FormError } from "@/components/Form";
import { HeartRateRangeForm } from "@/components/HeartRateRangeForm";
import { fetchTrends, formatAuthError } from "@/lib/api";
import {
  type HeartRateRange,
  readStoredHeartRateRange,
  storeHeartRateRange,
} from "@/lib/hrRange";
import type { TrendRangeKey, TrendsResponse } from "@/types/activity";

const RANGE_OPTIONS: { key: TrendRangeKey; label: string }[] = [
  { key: "4w", label: "4 weeks" },
  { key: "8w", label: "8 weeks" },
  { key: "3m", label: "3 months" },
  { key: "6m", label: "6 months" },
  { key: "1y", label: "1 year" },
  { key: "all", label: "All time" },
];

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: TrendsResponse }
  | { status: "error"; message: string };

export function TrendsPage() {
  const [rangeKey, setRangeKey] = useState<TrendRangeKey>("8w");
  const [hrRange, setHrRange] = useState<HeartRateRange>(readStoredHeartRateRange);
  const [draft, setDraft] = useState<HeartRateRange>(hrRange);
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    fetchTrends(rangeKey, hrRange.min, hrRange.max)
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
  }, [rangeKey, hrRange]);

  function applyHr(event: FormEvent) {
    event.preventDefault();
    if (draft.min >= draft.max) {
      setState({ status: "error", message: "The lower heart rate must be below the upper one." });
      return;
    }
    storeHeartRateRange(draft);
    setHrRange(draft);
  }

  return (
    <section className="flex flex-col gap-8">
      <div>
        <h1 className="font-display text-3xl">Trends</h1>
        <p className="mt-3 max-w-2xl text-ink-soft">
          Pace, heart rate, weekly distance, and how often you ran. Comparable pace uses the
          heart-rate range below — a filter, not a lab zone.
        </p>
      </div>

      <div className="flex flex-col gap-6 border border-rule bg-paper-2 px-4 py-4">
        <fieldset>
          <legend className="text-sm text-ink">Time range</legend>
          <div className="mt-3 flex flex-wrap gap-2">
            {RANGE_OPTIONS.map((option) => (
              <button
                key={option.key}
                type="button"
                onClick={() => setRangeKey(option.key)}
                className={
                  option.key === rangeKey
                    ? "bg-moss-deep px-3 py-2 text-paper"
                    : "border border-rule bg-paper px-3 py-2 text-ink hover:border-moss"
                }
                aria-pressed={option.key === rangeKey}
              >
                {option.label}
              </button>
            ))}
          </div>
        </fieldset>
        <form onSubmit={applyHr}>
          <HeartRateRangeForm range={draft} onChange={setDraft} />
          <button type="submit" className="mt-4 bg-moss-deep px-4 py-2 text-paper hover:bg-moss">
            Update heart-rate range
          </button>
        </form>
      </div>

      {state.status === "loading" ? (
        <p className="rounded-sm border border-rule bg-paper-2 px-4 py-3" role="status">
          Loading trends…
        </p>
      ) : null}
      {state.status === "error" ? <FormError message={state.message} /> : null}
      {state.status === "ready" ? <TrendsBody data={state.data} /> : null}
    </section>
  );
}

function TrendsBody({ data }: { data: TrendsResponse }) {
  return (
    <div className="flex flex-col gap-10">
      <ChartBlock
        title="Pace over time"
        description="Average pace per run. Faster sits toward the top."
      >
        <PaceOverTimeChart points={data.points} />
      </ChartBlock>
      <ChartBlock title="Average heart rate over time" description="Average beats per minute per run.">
        <HeartRateOverTimeChart points={data.points} />
      </ChartBlock>
      <ChartBlock title="Distance per week" description="Kilometres started in each Monday-based UTC week.">
        <WeeklyDistanceChart points={data.weekly} />
      </ChartBlock>
      <ChartBlock title="Running frequency" description="How many runs started in each week.">
        <WeeklyFrequencyChart points={data.weekly} />
      </ChartBlock>
      <ChartBlock
        title="Pace at comparable heart rate"
        description={`Easy-range pace scaled to the middle of ${data.heart_rate_min}–${data.heart_rate_max} bpm.`}
      >
        <ComparablePaceChart points={data.points} />
      </ChartBlock>
    </div>
  );
}

function ChartBlock({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section>
      <h2 className="font-display text-2xl">{title}</h2>
      <p className="mt-2 text-sm text-ink-soft">{description}</p>
      {children}
    </section>
  );
}
