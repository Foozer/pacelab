export interface StravaStatus {
  configured: boolean;
  connected: boolean;
  needs_reconnect: boolean;
  last_sync_at: string | null;
}
