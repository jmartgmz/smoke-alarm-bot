import logging

import discord
from discord.ext import commands

from smoke_alarm.config import Settings
from smoke_alarm.database import StatsDatabase
from smoke_alarm.cogs.leaderboard_cog import LeaderboardCog
from smoke_alarm.cogs.stats_cog import StatsCog
from smoke_alarm.cogs.voice_cog import VoiceCog
from smoke_alarm.voice_tracking import VoiceTracker

logger = logging.getLogger("smoke-alarm-bot")

PRESENCE_STATUS = discord.Status.dnd
PRESENCE_ACTIVITY = discord.Game(name="replace my batteries")


def create_bot(settings: Settings, db: StatsDatabase, tracker: VoiceTracker) -> commands.Bot:
    intents = discord.Intents.default()
    intents.voice_states = True

    bot = commands.Bot(
        command_prefix="!",
        intents=intents,
        status=PRESENCE_STATUS,
        activity=PRESENCE_ACTIVITY,
    )

    async def setup_hook() -> None:
        await bot.add_cog(VoiceCog(bot, settings, tracker))
        await bot.add_cog(StatsCog(db))
        await bot.add_cog(LeaderboardCog(db))

    bot.setup_hook = setup_hook

    async def apply_presence() -> None:
        await bot.change_presence(status=PRESENCE_STATUS, activity=PRESENCE_ACTIVITY)
        logger.info("Presence set to DND with activity text: replace my batteries")

    @bot.event
    async def on_ready() -> None:
        logger.info("Logged in as %s", bot.user)
        await apply_presence()

        guild_obj = discord.Object(id=settings.guild_id) if settings.guild_id else None
        if guild_obj is None:
            await bot.tree.sync()
            logger.info("Slash commands synced globally")
        else:
            await bot.tree.sync(guild=guild_obj)
            logger.info("Slash commands synced to guild %s", guild_obj.id)

    @bot.event
    async def on_resumed() -> None:
        await apply_presence()

    return bot
