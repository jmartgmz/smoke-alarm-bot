import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional, cast

import discord

from smoke_alarm.database import StatsDatabase


class VoiceTracker:
    def __init__(self, db: StatsDatabase, audio_file: str, interval_seconds: int, logger: logging.Logger) -> None:
        self.db = db
        self.audio_file = audio_file
        self.interval_seconds = interval_seconds
        self.logger = logger
        self._chirp_tasks: Dict[int, asyncio.Task] = {}
        self._last_chirp_at: Dict[int, float] = {}

    def get_seconds_until_next_chirp(self, guild_id: int) -> float:
        last_chirp_monotonic = self._last_chirp_at.get(guild_id)
        if last_chirp_monotonic is not None:
            return max(0.0, self.interval_seconds - (time.monotonic() - last_chirp_monotonic))

        persisted_last_chirp = self.db.get_last_chirp_at(guild_id)
        if persisted_last_chirp is None:
            return 0.0

        elapsed_seconds = (datetime.now(timezone.utc) - persisted_last_chirp).total_seconds()
        return max(0.0, self.interval_seconds - elapsed_seconds)

    async def start_chirp_loop(self, guild_id: int, voice_client: discord.VoiceClient) -> None:
        task = self._chirp_tasks.get(guild_id)
        if task and not task.done():
            task.cancel()

        self._chirp_tasks[guild_id] = asyncio.create_task(self._chirp_loop(guild_id, voice_client))

    async def stop_chirp_loop(self, guild_id: int) -> None:
        task = self._chirp_tasks.get(guild_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _chirp_loop(self, guild_id: int, voice_client: discord.VoiceClient) -> None:
        try:
            while True:
                if not voice_client.is_connected():
                    break

                seconds_until_next = self.get_seconds_until_next_chirp(guild_id)
                if seconds_until_next > 0:
                    await asyncio.sleep(seconds_until_next)
                    continue

                if not voice_client.is_playing():
                    source = discord.FFmpegPCMAudio(
                        self.audio_file,
                        before_options="-nostdin",
                        options="-loglevel panic",
                    )
                    voice_client.play(source)
                    self._last_chirp_at[guild_id] = time.monotonic()
                    self.db.set_last_chirp_at(guild_id)
                    listener_count = self.record_chirp_listeners(guild_id, voice_client)
                    self.logger.info(
                        "Chirp played in guild %s for %s listeners", guild_id, listener_count
                    )
                else:
                    # Audio is still in progress; check again soon without resetting cooldown.
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            self.logger.info("Chirp loop cancelled for guild %s", guild_id)
        finally:
            self._chirp_tasks.pop(guild_id, None)

    def record_chirp_listeners(self, guild_id: int, voice_client: discord.VoiceClient) -> int:
        channel = cast(discord.VoiceChannel, voice_client.channel)
        listeners = [member for member in channel.members if not member.bot]

        for member in listeners:
            self.db.increment_broke_meter(guild_id, member.id, 1)
            self.db.log_presence_event(
                guild_id=guild_id,
                channel_id=channel.id,
                user_id=member.id,
                event_type="chirp_heard",
                listened_chirp=1,
            )

        return len(listeners)

    def log_current_channel_members(self, guild_id: int, voice_client: discord.VoiceClient) -> None:
        channel = cast(discord.VoiceChannel, voice_client.channel)
        for member in channel.members:
            if member.bot:
                continue
            self.db.log_presence_event(
                guild_id=guild_id,
                channel_id=channel.id,
                user_id=member.id,
                event_type="present_with_bot",
                listened_chirp=0,
            )

    async def handle_voice_state_update(
        self,
        bot_user_id: int,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.id == bot_user_id:
            if before.channel and not after.channel:
                await self.stop_chirp_loop(member.guild.id)
            return

        if member.bot:
            return

        voice_client = cast(Optional[discord.VoiceClient], member.guild.voice_client)
        if not voice_client or not voice_client.channel:
            return

        bot_channel = cast(discord.VoiceChannel, voice_client.channel)

        joined_bot_channel = (
            after.channel
            and after.channel.id == bot_channel.id
            and (not before.channel or before.channel.id != bot_channel.id)
        )
        left_bot_channel = (
            before.channel
            and before.channel.id == bot_channel.id
            and (not after.channel or after.channel.id != bot_channel.id)
        )

        if joined_bot_channel:
            self.db.log_presence_event(
                guild_id=member.guild.id,
                channel_id=bot_channel.id,
                user_id=member.id,
                event_type="joined_bot_channel",
                listened_chirp=0,
            )
        elif left_bot_channel:
            self.db.log_presence_event(
                guild_id=member.guild.id,
                channel_id=bot_channel.id,
                user_id=member.id,
                event_type="left_bot_channel",
                listened_chirp=0,
            )
