import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    token: str
    audio_file: str
    interval_seconds: int
    guild_id: Optional[int]
    db_path: str

    @staticmethod
    def from_env() -> "Settings":
        load_dotenv()

        token = os.getenv("DISCORD_TOKEN", "").strip()
        audio_file = os.getenv("AUDIO_FILE", "assets/smoke-detector-beep.mp3").strip()
        interval_seconds = int(os.getenv("INTERVAL_SECONDS", "30").strip())
        guild_id_raw = os.getenv("GUILD_ID", "").strip()
        db_path = os.getenv("DB_PATH", "data/smoke_alarm.db").strip()

        if not token:
            raise RuntimeError("DISCORD_TOKEN is not set. Create a .env file and set it.")

        if not os.path.isfile(audio_file):
            raise RuntimeError(f"Audio file not found: {audio_file}")

        guild_id: Optional[int] = None
        if guild_id_raw:
            try:
                guild_id = int(guild_id_raw)
            except ValueError as exc:
                raise RuntimeError("GUILD_ID must be an integer if set.") from exc

        return Settings(
            token=token,
            audio_file=audio_file,
            interval_seconds=interval_seconds,
            guild_id=guild_id,
            db_path=db_path,
        )
