import type { ActivitySummary } from "@/types/activity";

export function formatDateTime(value: string | null): string {
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

export function formatDate(value: string | null): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

export function formatDistance(meters: number | null | undefined): string {
  if (meters == null) {
    return "—";
  }
  return `${(meters / 1000).toFixed(2)} km`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) {
    return "—";
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = Math.floor(seconds % 60);
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
  }
  return `${minutes}:${String(remainder).padStart(2, "0")}`;
}

export function formatElapsedTick(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.floor(seconds % 60);
  return `${minutes}:${String(remainder).padStart(2, "0")}`;
}

export function formatPaceSeconds(secondsPerKm: number | null | undefined): string {
  if (secondsPerKm == null || !Number.isFinite(secondsPerKm) || secondsPerKm <= 0) {
    return "—";
  }
  const minutes = Math.floor(secondsPerKm / 60);
  const seconds = Math.round(secondsPerKm % 60);
  if (seconds === 60) {
    return `${minutes + 1}:00/km`;
  }
  return `${minutes}:${String(seconds).padStart(2, "0")}/km`;
}

export function paceSecondsPerKm(activity: Pick<ActivitySummary, "distance_meters" | "duration_seconds">): number | null {
  if (activity.distance_meters == null || activity.duration_seconds == null) {
    return null;
  }
  if (activity.distance_meters < 1 || activity.duration_seconds < 1) {
    return null;
  }
  return activity.duration_seconds / (activity.distance_meters / 1000);
}

export function formatPace(activity: Pick<ActivitySummary, "distance_meters" | "duration_seconds">): string {
  return formatPaceSeconds(paceSecondsPerKm(activity));
}

export function paceFromSpeed(speedMetersPerSecond: number | null | undefined): number | null {
  if (speedMetersPerSecond == null || speedMetersPerSecond <= 0) {
    return null;
  }
  return 1000 / speedMetersPerSecond;
}
