from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class GuestCreate(BaseModel):
    install_id: str = Field(min_length=16, max_length=200)
    referral_code: str | None = Field(default=None, max_length=80)


class GuestOut(BaseModel):
    device_id: int
    device_token: str


class OtpRequest(BaseModel):
    email: EmailStr


class OtpVerify(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class LinkDevice(BaseModel):
    device_token: str


class ConfigResponse(BaseModel):
    free_speed_mbps: int
    ad_reward_minutes: int
    premium_prices: dict[str, int]
    max_heart_discount_percent: int
    heart_discount_tiers: dict[str, int]
    support_heart_tiers: dict[str, int]
    manual_card_number: str
    manual_card_holder: str
    tapsell_app_key: str
    tapsell_rewarded_zone_id: str
    timezone_name: str


class AdCompleteIn(BaseModel):
    nonce: str = Field(min_length=20, max_length=200)
    client_event_id: str = Field(min_length=8, max_length=120)
    provider_response_id: str | None = Field(default=None, max_length=180)


class FreeStatusOut(BaseModel):
    remaining_seconds: int
    earned_seconds: int
    consumed_seconds: int
    completed_ads: int
    reset_at: datetime


class VpnConnectIn(BaseModel):
    client_public_key: str = Field(min_length=44, max_length=44)
    server_id: int | None = None
    force_takeover: bool = False


class VpnConnectOut(BaseModel):
    session_id: int
    premium: bool
    client_address: str
    server_public_key: str
    endpoint: str
    dns: str
    allowed_ips: list[str]
    persistent_keepalive: int
    expires_at: datetime | None
    free_remaining_seconds_before_start: int | None
    server_id: int
    server_name: str
    country_code: str


class ServerOut(BaseModel):
    id: int
    name: str
    country_code: str
    city: str
    tier: str
    locked: bool
    available: bool = True


class ReportOut(BaseModel):
    today_seconds: int
    today_rx_bytes: int
    today_tx_bytes: int
    today_connections: int
    today_ads: int
    month_seconds: int
    month_bytes: int
    last_7_days: list[dict]


class AdminServerIn(BaseModel):
    name: str
    country_code: str = "DE"
    city: str = ""
    endpoint_host: str = Field(min_length=1, max_length=255)
    endpoint_port: int = 51820
    public_key: str
    dns: str = "1.1.1.1"
    client_cidr: str = "10.77.0.0/24"
    tier: str = "free"
    is_default: bool = False
    max_sessions: int = Field(default=200, ge=1, le=100000)
    agent_url: str | None = Field(default=None, max_length=255)
    agent_token: str | None = Field(default=None, max_length=255)


class AdminPaymentReview(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    admin_note: str | None = None
    hearts_to_grant: int | None = Field(default=None, ge=0, le=100000)
