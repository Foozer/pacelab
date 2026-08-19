export interface ProviderConnectionPublic {
  provider: string;
  last_sync_at: string | null;
}

export interface ProviderConnectionListResponse {
  items: ProviderConnectionPublic[];
}
