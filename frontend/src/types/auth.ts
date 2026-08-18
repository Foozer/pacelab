export interface UserPublic {
  id: string;
  email: string;
  email_verified: boolean;
  is_active: boolean;
  created_at: string;
}

export interface CsrfResponse {
  csrf_token: string;
}

export interface MessageResponse {
  message: string;
}

export interface DevOutboxItem {
  template: string;
  subject: string;
  body: string;
}

export interface DevOutboxResponse {
  emails: DevOutboxItem[];
}
