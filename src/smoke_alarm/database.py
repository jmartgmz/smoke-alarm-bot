import os
import sqlite3
from datetime import datetime, timezone


class StatsDatabase:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def init(self) -> None:
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_stats (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    broke_meter INTEGER NOT NULL DEFAULT 0,
                    last_seen_at TEXT NOT NULL,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS voice_presence_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    listened_chirp INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def log_presence_event(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        event_type: str,
        listened_chirp: int,
    ) -> None:
        now_iso = self._utc_now_iso()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO voice_presence_log (
                    guild_id, channel_id, user_id, event_type, listened_chirp, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (guild_id, channel_id, user_id, event_type, listened_chirp, now_iso),
            )
            conn.execute(
                """
                INSERT INTO user_stats (guild_id, user_id, broke_meter, last_seen_at)
                VALUES (?, ?, 0, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET last_seen_at=excluded.last_seen_at
                """,
                (guild_id, user_id, now_iso),
            )
            conn.commit()

    def increment_broke_meter(self, guild_id: int, user_id: int, amount: int = 1) -> int:
        now_iso = self._utc_now_iso()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO user_stats (guild_id, user_id, broke_meter, last_seen_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    broke_meter = user_stats.broke_meter + excluded.broke_meter,
                    last_seen_at = excluded.last_seen_at
                """,
                (guild_id, user_id, amount, now_iso),
            )
            row = conn.execute(
                "SELECT broke_meter FROM user_stats WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            ).fetchone()
            conn.commit()
        return int(row[0]) if row else 0

    def get_broke_meter(self, guild_id: int, user_id: int) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT broke_meter FROM user_stats WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            ).fetchone()
        return int(row[0]) if row else 0

    def get_server_leaderboard(self, guild_id: int, limit: int) -> list[tuple[int, int]]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT user_id, broke_meter
                FROM user_stats
                WHERE guild_id = ?
                ORDER BY broke_meter DESC, last_seen_at DESC
                LIMIT ?
                """,
                (guild_id, limit),
            ).fetchall()
        return [(int(row[0]), int(row[1])) for row in rows]

    def get_global_leaderboard(self, limit: int) -> list[tuple[int, int, int]]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT user_id, SUM(broke_meter) AS total_broke, COUNT(DISTINCT guild_id) AS guild_count
                FROM user_stats
                GROUP BY user_id
                ORDER BY total_broke DESC, MAX(last_seen_at) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [(int(row[0]), int(row[1]), int(row[2])) for row in rows]
