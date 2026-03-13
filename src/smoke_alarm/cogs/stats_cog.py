from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from smoke_alarm.database import StatsDatabase


class StatsCog(commands.Cog):
    def __init__(self, db: StatsDatabase) -> None:
        self.db = db

    @app_commands.command(name="stats", description="Show your current broke meter")
    @app_commands.describe(user="Optional user to check")
    async def stats(self, interaction: discord.Interaction, user: Optional[discord.Member] = None) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        target = user
        if target is None and isinstance(interaction.user, discord.Member):
            target = interaction.user

        if target is None:
            await interaction.response.send_message(
                "Could not determine which user to look up.", ephemeral=True
            )
            return

        broke_meter = self.db.get_broke_meter(interaction.guild_id, target.id)
        await interaction.response.send_message(
            f"{target.display_name} broke meter: {broke_meter}", ephemeral=True
        )
