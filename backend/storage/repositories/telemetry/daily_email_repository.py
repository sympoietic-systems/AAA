"""Short, atomic delivery claims shared by backend workers."""

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class DailyEmailRepository(BaseRepository):
    @with_connection
    def claim(self, date: str, recipient: str, now: float) -> bool:
        conn = self._conn()
        result = conn.execute(
            """INSERT INTO daily_email_deliveries(date, recipient, lease_until)
            VALUES (?, ?, ?) ON CONFLICT(date, recipient) DO UPDATE SET lease_until=excluded.lease_until
            WHERE sent_at IS NULL AND lease_until < ?""",
            (date, recipient, now + 3600, now),
        )
        conn.commit()
        return result.rowcount == 1

    @with_connection
    def mark_sent(self, date: str, recipient: str, now: float) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE daily_email_deliveries SET sent_at=? WHERE date=? AND recipient=?",
            (now, date, recipient),
        )
        conn.commit()

    @with_connection
    def release(self, date: str, recipient: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE daily_email_deliveries SET lease_until=0 WHERE date=? AND recipient=? AND sent_at IS NULL",
            (date, recipient),
        )
        conn.commit()
