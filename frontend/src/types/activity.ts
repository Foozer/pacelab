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

export type ActivityListResponse = {
  items: ActivitySummary[];
  total: number;
  limit: number;
  offset: number;
  last_sync_at: string | null;
};

export type ActivitySyncResponse = {
  provider: string;
  created: number;
  updated: number;
  total: number;
  last_sync_at: string;
};
