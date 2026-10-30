"""Alembic initial migration: all tables from spec section 10.

Revision: 001_initial (single initial revision for this scaffold).
Run: alembic upgrade head  (alembic.ini + env.py wiring is in README;
this file is the migration body, kept importable without alembic by
guarding the op import for syntax checks).
"""
try:
    from alembic import op  # type: ignore
    import sqlalchemy as sa  # type: ignore
except Exception:  # pragma: no cover
    op = None  # type: ignore
    sa = None  # type: ignore

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None

TABLES = ["users", "subscriptions", "usage_daily", "jobs", "job_results",
          "saved_items", "monitors", "webhook_events", "audit_logs",
          "admin_broadcasts", "admin_settings"]


def upgrade():
    if op is None:
        return
    op.create_table("users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger, unique=True, nullable=False, index=True),
        sa.Column("username", sa.String(64)), sa.Column("display_name", sa.String(128)),
        sa.Column("language", sa.String(8), server_default="id"),
        sa.Column("timezone", sa.String(64), server_default="Asia/Jakarta"),
        sa.Column("plan", sa.String(32), server_default="free"),
        sa.Column("status", sa.String(32), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("subscriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("plan", sa.String(32)), sa.Column("provider", sa.String(64)),
        sa.Column("provider_customer_id", sa.String(128)),
        sa.Column("status", sa.String(32), server_default="active"),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)))
    op.create_table("usage_daily",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("operation", sa.String(64)), sa.Column("requests", sa.Integer, server_default="0"),
        sa.Column("credits_estimated", sa.Integer, server_default="0"),
        sa.Column("bytes", sa.BigInteger, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_usage_daily_user_date", "user_id", "date"),
        sa.UniqueConstraint("user_id", "date", "operation"))
    op.create_table("jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("type", sa.String(64)), sa.Column("status", sa.String(32), server_default="queued"),
        sa.Column("input_hash", sa.String(64)),
        sa.Column("context_job_id", sa.String(128), index=True),
        sa.Column("progress", sa.Integer, server_default="0"),
        sa.Column("request_id", sa.String(128), index=True),
        sa.Column("error_code", sa.String(64)), sa.Column("error_message_safe", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_jobs_status_created", "status", "created_at"),
        sa.Index("ix_jobs_user_created", "user_id", "created_at"))
    op.create_table("job_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("jobs.id"), unique=True),
        sa.Column("result_type", sa.String(64)), sa.Column("payload_json", sa.JSON),
        sa.Column("storage_url", sa.String(512)), sa.Column("content_hash", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True)))
    op.create_table("saved_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("kind", sa.String(64)), sa.Column("title", sa.String(256)),
        sa.Column("url", sa.String(2048)), sa.Column("metadata_json", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("monitors",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("context_monitor_id", sa.String(128), index=True),
        sa.Column("target", sa.String(2048)), sa.Column("type", sa.String(64), server_default="page"),
        sa.Column("status", sa.String(32), server_default="active"),
        sa.Column("config_json", sa.JSON),
        sa.Column("last_event_at", sa.DateTime(timezone=True)))
    op.create_table("webhook_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("provider", sa.String(64)),
        sa.Column("event_id", sa.String(256), unique=True, index=True),
        sa.Column("payload_hash", sa.String(64)),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True)))
    op.create_table("audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("actor_user_id", sa.BigInteger, index=True),
        sa.Column("action", sa.String(128)), sa.Column("target_type", sa.String(64)),
        sa.Column("target_id", sa.String(128)), sa.Column("metadata_json", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("admin_broadcasts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("admin_id", sa.BigInteger), sa.Column("message", sa.Text),
        sa.Column("status", sa.String(32), server_default="draft"),
        sa.Column("counters", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    # Admin-panel API key storage (added before any deployment of 001):
    # encrypted_value holds Fernet ciphertext ONLY, never a plaintext key.
    op.create_table("admin_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key_name", sa.String(128), unique=True, nullable=False, index=True),
        sa.Column("encrypted_value", sa.Text, nullable=False),
        sa.Column("updated_by", sa.BigInteger),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade():
    if op is None:
        return
    for table in reversed(TABLES):
        op.drop_table(table)
