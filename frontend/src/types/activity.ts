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

export type UpcomingMetric = {
  available: false;
  label: string;
  note: string;
};

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
  five_k_estimate: UpcomingMetric;
  easy_pace: UpcomingMetric;
  aerobic_efficiency: UpcomingMetric;
};
