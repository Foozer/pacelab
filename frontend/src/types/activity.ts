export type ActivitySummary = {
  id: string;
  provider: string;
  provider_activity_id: string;
  activity_type: string | null;
  started_at: string | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  average_speed: number | null;
  average_heart_rate: number | null;
  max_heart_rate: number | null;
  average_cadence: number | null;
  elevation_gain: number | null;
  calories: number | null;
  created_at: string;
  updated_at: string;
};

export type ActivitySample = {
  timestamp: string;
  elapsed_seconds: number;
  distance_meters: number | null;
  heart_rate: number | null;
  speed: number | null;
  cadence: number | null;
  elevation: number | null;
};

export type ActivityDetail = ActivitySummary & {
  samples: ActivitySample[];
};

export type ActivityListQuery = {
  limit: number;
  offset: number;
  fromDate?: string;
  toDate?: string;
  activityType?: string;
};

export type ActivityListResponse = {
  items: ActivitySummary[];
  total: number;
  limit: number;
  offset: number;
  last_sync_at: string | null;
  activity_types: string[];
};

export type ActivitySyncResponse = {
  provider: string;
  created: number;
  updated: number;
  total: number;
  last_sync_at: string;
};

export type UnavailableMetric = {
  available: false;
  label: string;
  headline: string;
  note: string;
};

export type FiveKEstimateAvailable = {
  available: true;
  label: string;
  headline: string;
  note: string;
  estimated_seconds: number;
  qualifying_run_count: number;
};

export type EasyPaceAvailable = {
  available: true;
  label: string;
  headline: string;
  note: string;
  pace_seconds_per_km: number;
  comparable_pace_seconds_per_km: number;
  average_heart_rate: number;
  run_count: number;
  heart_rate_min: number;
  heart_rate_max: number;
};

export type AerobicEfficiencyAvailable = {
  available: true;
  label: string;
  headline: string;
  note: string;
  direction: "improving" | "stable" | "declining" | "not_enough_data";
  direction_label: string;
  score: number | null;
  relative_change_percent: number | null;
  qualifying_run_count: number;
};

export type FiveKEstimateMetric = FiveKEstimateAvailable | UnavailableMetric;
export type EasyPaceMetric = EasyPaceAvailable | UnavailableMetric;
export type AerobicEfficiencyMetric = AerobicEfficiencyAvailable | UnavailableMetric;

export type WeeklyVolume = {
  run_count: number;
  distance_meters: number;
  duration_seconds: number;
  period_start: string;
  period_end: string;
};

export type PaceHeartRatePoint = {
  activity_id: string;
  started_at: string;
  pace_seconds_per_km: number | null;
  average_heart_rate: number | null;
  distance_meters: number | null;
};

export type DashboardResponse = {
  weekly: WeeklyVolume;
  recent_activities: ActivitySummary[];
  pace_heart_rate_trend: PaceHeartRatePoint[];
  five_k_estimate: FiveKEstimateMetric;
  easy_pace: EasyPaceMetric;
  aerobic_efficiency: AerobicEfficiencyMetric;
};

export type EasyRunningPoint = {
  activity_id: string | null;
  started_at: string;
  pace_seconds_per_km: number;
  heart_rate: number;
  comparable_pace_seconds_per_km: number;
  distance_meters: number;
};

export type EasyRunningResponse = {
  heart_rate_min: number;
  heart_rate_max: number;
  run_count: number;
  distance_meters: number;
  average_pace_seconds_per_km: number | null;
  average_heart_rate: number | null;
  comparable_pace_seconds_per_km: number | null;
  headline: string;
  note: string;
  points: EasyRunningPoint[];
};

export type AerobicPoint = {
  activity_id: string | null;
  started_at: string;
  score: number;
  pace_seconds_per_km: number;
  heart_rate: number;
};

export type AerobicEfficiencyResponse = {
  metric: AerobicEfficiencyMetric;
  points: AerobicPoint[];
};

export type TrendActivityPoint = {
  activity_id: string | null;
  started_at: string;
  pace_seconds_per_km: number | null;
  average_heart_rate: number | null;
  distance_meters: number | null;
  comparable_pace_seconds_per_km: number | null;
};

export type WeeklyTrendPoint = {
  week_start: string;
  distance_meters: number;
  run_count: number;
};

export type TrendsResponse = {
  range_key: string;
  period_start: string | null;
  period_end: string;
  heart_rate_min: number;
  heart_rate_max: number;
  points: TrendActivityPoint[];
  weekly: WeeklyTrendPoint[];
};

export type TrendRangeKey = "4w" | "8w" | "3m" | "6m" | "1y" | "all";

