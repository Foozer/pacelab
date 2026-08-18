export type HealthStatus = "ok" | "unhealthy";
export type DatabaseStatus = "connected" | "disconnected";

export interface HealthResponse {
  status: HealthStatus;
  database: DatabaseStatus;
  version: string;
  environment: string;
}
