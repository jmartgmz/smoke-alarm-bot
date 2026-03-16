from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from smoke_alarm.database import StatsDatabase


class StatsCog(commands.Cog):
    def __init__(self, db: StatsDatabase) -> None:
        self.db = db

    @app_commands.command(name="userstats", description="Show your stats, or mention a user to view theirs")
    @app_commands.describe(user="Optional user to check")
    async def user_stats(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        target = user or interaction.user
        broke_meter = self.db.get_broke_meter(interaction.guild_id, target.id)
        display_name = (
            target.display_name
            if isinstance(target, discord.Member)
            else target.name
        )
        embed = _create_stats_embed(display_name, broke_meter)
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)


ACCENT_RED_COLOR = discord.Color.from_rgb(222, 49, 57)


def _create_stats_embed(display_name: str, broke_meter: int) -> discord.Embed:
    embed = discord.Embed(
        title="User Stats",
        description=f"**{display_name}** has a broke meter of **{broke_meter}**.",
        color=ACCENT_RED_COLOR,
    )
    embed.set_footer(text="Smoke Alarm Bot")
    return embed

