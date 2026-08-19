import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatDate, formatElapsedTick, formatPaceSeconds, paceFromSpeed } from "@/lib/format";
import type {
  ActivitySample,
  EasyRunningPoint,
  PaceHeartRatePoint,
  TrendActivityPoint,
  WeeklyTrendPoint,
} from "@/types/activity";

const moss = "#3a5a48";
const copper = "#b45a32";
const rule = "#d4cbb8";
const inkSoft = "#4b5346";

type PacePoint = { elapsed: number; pace: number };
type HeartRatePoint = { elapsed: number; heartRate: number };
type PaceHeartSample = { heartRate: number; pace: number };

function sampleSeries(samples: ActivitySample[]): {
  pace: PacePoint[];
  heartRate: HeartRatePoint[];
  paceVsHeartRate: PaceHeartSample[];
} {
  const pace: PacePoint[] = [];
  const heartRate: HeartRatePoint[] = [];
  const paceVsHeartRate: PaceHeartSample[] = [];
  for (const sample of samples) {
    const paceSeconds = paceFromSpeed(sample.speed);
    if (paceSeconds != null) {
      pace.push({ elapsed: sample.elapsed_seconds, pace: paceSeconds });
    }
    if (sample.heart_rate != null && sample.heart_rate > 0) {
      heartRate.push({ elapsed: sample.elapsed_seconds, heartRate: sample.heart_rate });
    }
    if (paceSeconds != null && sample.heart_rate != null && sample.heart_rate > 0) {
      paceVsHeartRate.push({ heartRate: sample.heart_rate, pace: paceSeconds });
    }
  }
  return { pace, heartRate, paceVsHeartRate };
}

function ChartFrame({
  title,
  description,
  children,
  empty,
}: {
  title: string;
  description: string;
  children: ReactNode;
  empty: boolean;
}) {
  return (
    <figure className="border border-rule bg-paper-2 px-4 py-4">
      <figcaption>
        <h3 className="font-display text-xl">{title}</h3>
        <p className="mt-1 text-sm text-ink-soft">{description}</p>
      </figcaption>
      {empty ? (
        <p className="mt-6 text-sm text-ink-soft">No samples to chart for this run.</p>
      ) : (
        <div className="mt-4 h-56 w-full">{children}</div>
      )}
    </figure>
  );
}

export function ActivitySampleCharts({ samples }: { samples: ActivitySample[] }) {
  const series = sampleSeries(samples);
  return (
    <div className="grid grid-cols-1 gap-6">
      <ChartFrame
        title="Pace"
        description="Seconds per kilometre over the run. Faster is toward the top."
        empty={series.pace.length === 0}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series.pace} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
            <CartesianGrid stroke={rule} strokeDasharray="3 3" />
            <XAxis
              dataKey="elapsed"
              tickFormatter={formatElapsedTick}
              stroke={inkSoft}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              dataKey="pace"
              reversed
              tickFormatter={(value: number) => formatPaceSeconds(value).replace("/km", "")}
              stroke={inkSoft}
              tick={{ fontSize: 12 }}
              width={48}
            />
            <Tooltip
              content={({ active, payload }) => {
                const point = payload?.[0]?.payload as PacePoint | undefined;
                if (!active || !point) {
                  return null;
                }
                return (
                  <div className="border border-rule bg-paper px-3 py-2 text-sm">
                    <p>{formatElapsedTick(point.elapsed)}</p>
                    <p className="text-moss-deep">{formatPaceSeconds(point.pace)}</p>
                  </div>
                );
              }}
            />
            <Line type="monotone" dataKey="pace" stroke={moss} dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </ChartFrame>

      <ChartFrame
        title="Heart rate"
        description="Beats per minute over the run."
        empty={series.heartRate.length === 0}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series.heartRate} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
            <CartesianGrid stroke={rule} strokeDasharray="3 3" />
            <XAxis
              dataKey="elapsed"
              tickFormatter={formatElapsedTick}
              stroke={inkSoft}
              tick={{ fontSize: 12 }}
            />
            <YAxis dataKey="heartRate" stroke={inkSoft} tick={{ fontSize: 12 }} width={40} />
            <Tooltip
              content={({ active, payload }) => {
                const point = payload?.[0]?.payload as HeartRatePoint | undefined;
                if (!active || !point) {
                  return null;
                }
                return (
                  <div className="border border-rule bg-paper px-3 py-2 text-sm">
                    <p>{formatElapsedTick(point.elapsed)}</p>
                    <p className="text-copper">{point.heartRate} bpm</p>
                  </div>
                );
              }}
            />
            <Line type="monotone" dataKey="heartRate" stroke={copper} dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </ChartFrame>

      <ChartFrame
        title="Pace versus heart rate"
        description="Each point is a sample. Lower and to the left is easier relative effort."
        empty={series.paceVsHeartRate.length === 0}
      >
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
            <CartesianGrid stroke={rule} strokeDasharray="3 3" />
            <XAxis
              dataKey="heartRate"
              type="number"
              name="Heart rate"
              unit=" bpm"
              stroke={inkSoft}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              dataKey="pace"
              type="number"
              reversed
              tickFormatter={(value: number) => formatPaceSeconds(value).replace("/km", "")}
              stroke={inkSoft}
              tick={{ fontSize: 12 }}
              width={48}
            />
            <Tooltip
              content={({ active, payload }) => {
                const point = payload?.[0]?.payload as PaceHeartSample | undefined;
                if (!active || !point) {
                  return null;
                }
                return (
                  <div className="border border-rule bg-paper px-3 py-2 text-sm">
                    <p>{point.heartRate} bpm</p>
                    <p className="text-moss-deep">{formatPaceSeconds(point.pace)}</p>
                  </div>
                );
              }}
            />
            <Scatter data={series.paceVsHeartRate} fill={moss} />
          </ScatterChart>
        </ResponsiveContainer>
      </ChartFrame>
    </div>
  );
}

export function DashboardTrendChart({ points }: { points: PaceHeartRatePoint[] }) {
  const data = points.filter(
    (point) => point.pace_seconds_per_km != null || point.average_heart_rate != null,
  );
  if (data.length === 0) {
    return (
      <p className="mt-4 text-sm text-ink-soft">Import some runs to see pace and heart rate here.</p>
    );
  }

  return (
    <div className="mt-4 h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
          <CartesianGrid stroke={rule} strokeDasharray="3 3" />
          <XAxis
            dataKey="started_at"
            tickFormatter={(value: string) => formatDate(value)}
            stroke={inkSoft}
            tick={{ fontSize: 12 }}
            minTickGap={24}
          />
          <YAxis
            yAxisId="pace"
            reversed
            tickFormatter={(value: number) => formatPaceSeconds(value).replace("/km", "")}
            stroke={moss}
            tick={{ fontSize: 12 }}
            width={48}
          />
          <YAxis
            yAxisId="hr"
            orientation="right"
            stroke={copper}
            tick={{ fontSize: 12 }}
            width={36}
          />
          <Tooltip
            content={({ active, payload }) => {
              const point = payload?.[0]?.payload as PaceHeartRatePoint | undefined;
              if (!active || !point) {
                return null;
              }
              return (
                <div className="border border-rule bg-paper px-3 py-2 text-sm">
                  <p>{formatDate(point.started_at)}</p>
                  <p className="text-moss-deep">{formatPaceSeconds(point.pace_seconds_per_km)}</p>
                  <p className="text-copper">
                    {point.average_heart_rate != null ? `${point.average_heart_rate} bpm` : "—"}
                  </p>
                </div>
              );
            }}
          />
          <Line
            yAxisId="pace"
            type="monotone"
            dataKey="pace_seconds_per_km"
            stroke={moss}
            dot={{ r: 3 }}
            connectNulls
            strokeWidth={2}
          />
          <Line
            yAxisId="hr"
            type="monotone"
            dataKey="average_heart_rate"
            stroke={copper}
            dot={{ r: 3 }}
            connectNulls
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function PaceLineChart({
  data,
  dataKey,
  emptyLabel,
}: {
  data: Array<Record<string, unknown>>;
  dataKey: string;
  emptyLabel: string;
}) {
  if (data.length === 0) {
    return <p className="mt-4 text-sm text-ink-soft">{emptyLabel}</p>;
  }
  return (
    <div className="mt-4 h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid stroke={rule} strokeDasharray="3 3" />
          <XAxis
            dataKey="started_at"
            tickFormatter={(value: string) => formatDate(value)}
            stroke={inkSoft}
            tick={{ fontSize: 12 }}
            minTickGap={24}
          />
          <YAxis
            reversed
            tickFormatter={(value: number) => formatPaceSeconds(value).replace("/km", "")}
            stroke={moss}
            tick={{ fontSize: 12 }}
            width={48}
          />
          <Tooltip
            content={({ active, payload }) => {
              const point = payload?.[0]?.payload as { started_at?: string } | undefined;
              const pace = payload?.[0]?.value;
              if (!active || !point || typeof pace !== "number") {
                return null;
              }
              return (
                <div className="border border-rule bg-paper px-3 py-2 text-sm">
                  <p>{formatDate(point.started_at ?? null)}</p>
                  <p className="text-moss-deep">{formatPaceSeconds(pace)}</p>
                </div>
              );
            }}
          />
          <Line type="monotone" dataKey={dataKey} stroke={moss} dot={{ r: 3 }} connectNulls strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function EasyPaceTrendChart({ points }: { points: EasyRunningPoint[] }) {
  return (
    <PaceLineChart
      data={points}
      dataKey="comparable_pace_seconds_per_km"
      emptyLabel="No easy runs in this heart-rate range yet."
    />
  );
}

export function PaceOverTimeChart({ points }: { points: TrendActivityPoint[] }) {
  return (
    <PaceLineChart
      data={points.filter((point) => point.pace_seconds_per_km != null)}
      dataKey="pace_seconds_per_km"
      emptyLabel="No pace points in this range."
    />
  );
}

export function HeartRateOverTimeChart({ points }: { points: TrendActivityPoint[] }) {
  const data = points.filter((point) => point.average_heart_rate != null);
  if (data.length === 0) {
    return <p className="mt-4 text-sm text-ink-soft">No heart-rate points in this range.</p>;
  }
  return (
    <div className="mt-4 h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid stroke={rule} strokeDasharray="3 3" />
          <XAxis
            dataKey="started_at"
            tickFormatter={(value: string) => formatDate(value)}
            stroke={inkSoft}
            tick={{ fontSize: 12 }}
            minTickGap={24}
          />
          <YAxis stroke={copper} tick={{ fontSize: 12 }} width={40} />
          <Tooltip
            content={({ active, payload }) => {
              const point = payload?.[0]?.payload as TrendActivityPoint | undefined;
              if (!active || !point) {
                return null;
              }
              return (
                <div className="border border-rule bg-paper px-3 py-2 text-sm">
                  <p>{formatDate(point.started_at)}</p>
                  <p className="text-copper">
                    {point.average_heart_rate != null ? `${Math.round(point.average_heart_rate)} bpm` : "—"}
                  </p>
                </div>
              );
            }}
          />
          <Line
            type="monotone"
            dataKey="average_heart_rate"
            stroke={copper}
            dot={{ r: 3 }}
            connectNulls
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ComparablePaceChart({ points }: { points: TrendActivityPoint[] }) {
  return (
    <PaceLineChart
      data={points.filter((point) => point.comparable_pace_seconds_per_km != null)}
      dataKey="comparable_pace_seconds_per_km"
      emptyLabel="No runs in the chosen heart-rate range in this window."
    />
  );
}

export function WeeklyDistanceChart({ points }: { points: WeeklyTrendPoint[] }) {
  if (points.length === 0) {
    return <p className="mt-4 text-sm text-ink-soft">No weekly distance to chart yet.</p>;
  }
  return (
    <div className="mt-4 h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid stroke={rule} strokeDasharray="3 3" />
          <XAxis
            dataKey="week_start"
            tickFormatter={(value: string) => formatDate(value)}
            stroke={inkSoft}
            tick={{ fontSize: 12 }}
            minTickGap={24}
          />
          <YAxis
            tickFormatter={(value: number) => `${(value / 1000).toFixed(0)}`}
            stroke={moss}
            tick={{ fontSize: 12 }}
            width={36}
          />
          <Tooltip
            content={({ active, payload }) => {
              const point = payload?.[0]?.payload as WeeklyTrendPoint | undefined;
              if (!active || !point) {
                return null;
              }
              return (
                <div className="border border-rule bg-paper px-3 py-2 text-sm">
                  <p>Week of {formatDate(point.week_start)}</p>
                  <p className="text-moss-deep">{(point.distance_meters / 1000).toFixed(1)} km</p>
                </div>
              );
            }}
          />
          <Bar dataKey="distance_meters" fill={moss} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function WeeklyFrequencyChart({ points }: { points: WeeklyTrendPoint[] }) {
  if (points.length === 0) {
    return <p className="mt-4 text-sm text-ink-soft">No weekly frequency to chart yet.</p>;
  }
  return (
    <div className="mt-4 h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid stroke={rule} strokeDasharray="3 3" />
          <XAxis
            dataKey="week_start"
            tickFormatter={(value: string) => formatDate(value)}
            stroke={inkSoft}
            tick={{ fontSize: 12 }}
            minTickGap={24}
          />
          <YAxis allowDecimals={false} stroke={moss} tick={{ fontSize: 12 }} width={28} />
          <Tooltip
            content={({ active, payload }) => {
              const point = payload?.[0]?.payload as WeeklyTrendPoint | undefined;
              if (!active || !point) {
                return null;
              }
              return (
                <div className="border border-rule bg-paper px-3 py-2 text-sm">
                  <p>Week of {formatDate(point.week_start)}</p>
                  <p className="text-moss-deep">
                    {point.run_count} {point.run_count === 1 ? "run" : "runs"}
                  </p>
                </div>
              );
            }}
          />
          <Bar dataKey="run_count" fill={moss} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
