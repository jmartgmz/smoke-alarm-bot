import time
from typing import Optional, cast

import discord
from discord import app_commands
from discord.ext import commands

from smoke_alarm.config import Settings
from smoke_alarm.voice_tracking import VoiceTracker


class VoiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot, settings: Settings, tracker: VoiceTracker) -> None:
        self.bot = bot
        self.settings = settings
        self.tracker = tracker
        self._last_toggle_at: dict[int, float] = {}

    def _is_toggle_rate_limited(self, guild_id: int, min_seconds: float = 3.0) -> bool:
        now = time.monotonic()
        last_toggle_at = self._last_toggle_at.get(guild_id)
        if last_toggle_at is not None and now - last_toggle_at < min_seconds:
            return True
        self._last_toggle_at[guild_id] = now
        return False

    @app_commands.command(name="join", description="Join your voice channel and start chirping")
    async def join(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        if self._is_toggle_rate_limited(interaction.guild_id):
            await interaction.response.send_message(
                "Join/leave is cooling down for a moment. Try again in a few seconds.",
                ephemeral=True,
            )
            return

        if not interaction.user or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Could not determine your voice channel.", ephemeral=True
            )
            return

        voice_state = interaction.user.voice
        if not voice_state or not voice_state.channel:
            await interaction.response.send_message(
                "You need to be in a voice channel first.", ephemeral=True
            )
            return

        channel = voice_state.channel
        voice_client = (
            cast(Optional[discord.VoiceClient], interaction.guild.voice_client)
            if interaction.guild
            else None
        )

        if voice_client and voice_client.is_connected():
            await voice_client.move_to(channel)
        else:
            voice_client = cast(discord.VoiceClient, await channel.connect())

        self.tracker.log_current_channel_members(interaction.guild_id, voice_client)
        await self.tracker.start_chirp_loop(interaction.guild_id, voice_client)
        await interaction.response.send_message(
            f"Joined {channel.name} and started chirping every {self.settings.interval_seconds} seconds.",
            ephemeral=True,
        )

    @app_commands.command(name="leave", description="Stop chirping and disconnect")
    async def leave(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        if self._is_toggle_rate_limited(interaction.guild_id):
            await interaction.response.send_message(
                "Join/leave is cooling down for a moment. Try again in a few seconds.",
                ephemeral=True,
            )
            return

        voice_client = (
            cast(Optional[discord.VoiceClient], interaction.guild.voice_client)
            if interaction.guild
            else None
        )
        if not voice_client or not voice_client.is_connected():
            await interaction.response.send_message(
                "I am not connected to a voice channel.", ephemeral=True
            )
            return

        await self.tracker.stop_chirp_loop(interaction.guild_id)
        await voice_client.disconnect(force=True)
        await interaction.response.send_message("Disconnected.", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if not self.bot.user:
            return
        await self.tracker.handle_voice_state_update(self.bot.user.id, member, before, after)
