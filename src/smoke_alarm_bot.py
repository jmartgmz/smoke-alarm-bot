import logging
from smoke_alarm.bot_app import create_bot
from smoke_alarm.config import Settings
from smoke_alarm.database import StatsDatabase
from smoke_alarm.voice_tracking import VoiceTracker


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("smoke-alarm-bot")

    settings = Settings.from_env()
    db = StatsDatabase(settings.db_path)
    db.init()

    tracker = VoiceTracker(
        db=db,
        audio_file=settings.audio_file,
        interval_seconds=settings.interval_seconds,
        logger=logger,
    )
    bot = create_bot(settings, db, tracker)
    bot.run(settings.token)


if __name__ == "__main__":
    main()
