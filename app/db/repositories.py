"""Repository pattern (async SQLAlchemy). Parameterized queries only --
no string-built SQL, no user input in SQL text."""
from __future__ import annotations

from sqlalchemy import delete, select

from .models import AdminSetting, AuditLog, Job, JobResult, Monitor, User, WebhookEvent


class UserRepository:
    def __init__(self, session):
        self.session = session

    async def get_or_create_by_telegram_id(self, telegram_user_id: int, **kwargs) -> User:
        user = await self.session.scalar(
            select(User).where(User.telegram_user_id == telegram_user_id))
        if user is None:
            user = User(telegram_user_id=telegram_user_id, **kwargs)
            self.session.add(user)
            await self.session.flush()
        return user

    async def delete_user_data(self, telegram_user_id: int) -> int:
        """Delete a user's jobs/results/monitors/saved data + the user row.
        Returns number of job rows deleted. Caller must audit-log this."""
        user = await self.session.scalar(
            select(User).where(User.telegram_user_id == telegram_user_id))
        if user is None:
            return 0
        job_ids = [r for r in (await self.session.scalars(
            select(Job.id).where(Job.user_id == user.id)))]
        if job_ids:
            await self.session.execute(delete(JobResult).where(JobResult.job_id.in_(job_ids)))
            await self.session.execute(delete(Job).where(Job.id.in_(job_ids)))
        await self.session.execute(delete(Monitor).where(Monitor.user_id == user.id))
        await self.session.delete(user)
        return len(job_ids)


class JobRepository:
    def __init__(self, session):
        self.session = session

    async def create(self, **kwargs) -> Job:
        job = Job(**kwargs)
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_for_user(self, job_id: int, user_id: int):
        """Ownership-enforced read: a user can only see their own jobs."""
        job = await self.session.get(Job, job_id)
        if job is None:
            return None
        user = await self.session.get(User, job.user_id)
        return job if user and user.telegram_user_id == user_id else None

    async def delete_expired_results(self, now) -> int:
        result = await self.session.execute(
            delete(JobResult).where(JobResult.expires_at.is_not(None))
            .where(JobResult.expires_at <= now))
        return result.rowcount or 0


class AuditRepository:
    def __init__(self, session):
        self.session = session

    async def log(self, actor_user_id, action, target_type=None, target_id=None,
                  metadata=None) -> AuditLog:
        entry = AuditLog(actor_user_id=actor_user_id, action=action,
                         target_type=target_type, target_id=str(target_id) if target_id else None,
                         metadata_json=metadata or {})
        self.session.add(entry)
        await self.session.flush()
        return entry


class AdminSettingRepository:
    """admin_settings: encrypted values only, never plaintext keys."""

    def __init__(self, session):
        self.session = session

    async def get_encrypted(self, key_name: str):
        row = await self.session.scalar(
            select(AdminSetting).where(AdminSetting.key_name == key_name))
        return row.encrypted_value if row else None

    async def set_encrypted(self, key_name: str, token: str, updated_by=None) -> None:
        row = await self.session.scalar(
            select(AdminSetting).where(AdminSetting.key_name == key_name))
        if row is None:
            self.session.add(AdminSetting(key_name=key_name,
                                          encrypted_value=token, updated_by=updated_by))
        else:
            row.encrypted_value = token
            row.updated_by = updated_by
        await self.session.flush()

    async def delete(self, key_name: str) -> None:
        await self.session.execute(delete(AdminSetting).where(AdminSetting.key_name == key_name))


class WebhookEventRepository:
    def __init__(self, session):
        self.session = session

    async def already_seen(self, event_id: str) -> bool:
        row = await self.session.scalar(
            select(WebhookEvent).where(WebhookEvent.event_id == event_id))
        return row is not None
