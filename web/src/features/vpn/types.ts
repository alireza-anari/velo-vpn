export type VpnServerSummary = {
  id: number;
  name: string;
  country_code: string;
  city: string;
};

export type WebVpnAccess = {
  provisioned: boolean;
  active: boolean;
  peer_enabled: boolean;
  access_until: string | null;
  remaining_seconds: number;
  premium: boolean;
  welcome_available: boolean;
  welcome_minutes: number;
  config_version: number | null;
  server: VpnServerSummary | null;
};

export type IssuedVpnConfig = {
  access: WebVpnAccess;
  configuration: string;
  filename: string;
};
