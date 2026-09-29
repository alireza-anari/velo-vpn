from __future__ import annotations

from datetime import date, datetime, timezone
from sqlalchemy import (
    String, Integer, DateTime, Boolean, ForeignKey, Text, BigInteger,
    Date, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    referral_code: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    install_id_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)


class OtpCode(Base):
    __tablename__ = "otp_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    code_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HeartLedger(Base):
    __tablename__ = "heart_ledger"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(80))
    reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(40), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ManualPayment(Base):
    __tablename__ = "manual_payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    amount_toman: Mapped[int] = mapped_column(BigInteger)
    plan_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    requested_hearts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    receipt_path: Mapped[str] = mapped_column(Text)
    receipt_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    target_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    target_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[int] = mapped_column(primary_key=True)
    inviter_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    invited_device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), unique=True)
    invited_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    install_rewarded: Mapped[bool] = mapped_column(Boolean, default=False)
    rewarded_days: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ReferralDailyReward(Base):
    __tablename__ = "referral_daily_rewards"
    __table_args__ = (UniqueConstraint("referral_id", "local_date", name="uq_referral_day"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    referral_id: Mapped[int] = mapped_column(ForeignKey("referrals.id"), index=True)
    local_date: Mapped[date] = mapped_column(Date, index=True)
    hearts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MissionInteraction(Base):
    __tablename__ = "mission_interactions"
    __table_args__ = (UniqueConstraint("user_id", "mission_key", name="uq_mission_interaction_user_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    mission_key: Mapped[str] = mapped_column(String(80), index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MissionClaim(Base):
    __tablename__ = "mission_claims"
    __table_args__ = (UniqueConstraint("user_id", "mission_key", "period_key", name="uq_mission_user_period"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    mission_key: Mapped[str] = mapped_column(String(80), index=True)
    period_key: Mapped[str] = mapped_column(String(40), index=True)
    hearts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class FreeUsageDay(Base):
    __tablename__ = "free_usage_days"
    __table_args__ = (UniqueConstraint("device_id", "local_date", name="uq_free_usage_device_day"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    local_date: Mapped[date] = mapped_column(Date, index=True)
    earned_seconds: Mapped[int] = mapped_column(Integer, default=0)
    consumed_seconds: Mapped[int] = mapped_column(Integer, default=0)
    completed_ads: Mapped[int] = mapped_column(Integer, default=0)
    connection_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AdChallenge(Base):
    __tablename__ = "ad_challenges"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    nonce_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(30), default="tapsell")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RewardEvent(Base):
    __tablename__ = "reward_events"
    __table_args__ = (UniqueConstraint("device_id", "client_event_id", name="uq_reward_device_event"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(30), default="tapsell")
    client_event_id: Mapped[str] = mapped_column(String(120))
    provider_response_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    reward_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VpnServer(Base):
    __tablename__ = "vpn_servers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    country_code: Mapped[str] = mapped_column(String(8), default="DE")
    city: Mapped[str] = mapped_column(String(80), default="")
    endpoint_host: Mapped[str] = mapped_column(String(255))
    endpoint_port: Mapped[int] = mapped_column(Integer, default=51820)
    public_key: Mapped[str] = mapped_column(String(80))
    dns: Mapped[str] = mapped_column(String(80), default="1.1.1.1")
    client_cidr: Mapped[str] = mapped_column(String(64), default="10.77.0.0/24")
    tier: Mapped[str] = mapped_column(String(20), default="free")  # free|premium|vip
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    max_sessions: Mapped[int] = mapped_column(Integer, default=200)
    # Optional remote node-agent. When empty, the API manages the local WireGuard host.
    agent_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    health_state: Mapped[str] = mapped_column(String(20), default="unknown", index=True)
    health_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_health_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    unhealthy_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VpnSession(Base):
    __tablename__ = "vpn_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("vpn_servers.id"), index=True)
    client_public_key: Mapped[str] = mapped_column(String(80), index=True)
    client_ip: Mapped[str] = mapped_column(String(64), index=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_seconds: Mapped[int] = mapped_column(Integer, default=0)
    rx_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    tx_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    disconnect_reason: Mapped[str | None] = mapped_column(String(60), nullable=True)
    reconnect_required: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

class StorePurchase(Base):
    __tablename__ = "store_purchases"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    sku: Mapped[str] = mapped_column(String(80), index=True)
    hearts_spent: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class UserEntitlement(Base):
    __tablename__ = "user_entitlements"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    sku: Mapped[str] = mapped_column(String(80), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    target: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
