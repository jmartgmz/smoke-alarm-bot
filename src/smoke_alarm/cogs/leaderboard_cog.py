from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from smoke_alarm.database import StatsDatabase


class LeaderboardCog(commands.Cog):
    def __init__(self, db: StatsDatabase) -> None:
        self.db = db

    @app_commands.command(name="localstats", description="Show broke meter stats for this server")
    @app_commands.describe(limit="How many users to show (1-25)")
    async def local_stats(self, interaction: discord.Interaction, limit: Optional[int] = 10) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        safe_limit = max(1, min(limit or 10, 25))
        rows = self.db.get_server_leaderboard(interaction.guild_id, safe_limit)
        if not rows:
            await interaction.response.send_message(
                "No local stats yet for this server.", ephemeral=True
            )
            return

        lines = [f"Local Stats | Top {safe_limit}"]
        for rank, (user_id, broke_meter) in enumerate(rows, start=1):
            lines.append(f"{rank}. <@{user_id}> | broke meter: {broke_meter}")

        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="globalstats", description="Show broke meter stats across all servers")
    @app_commands.describe(limit="How many users to show (1-25)")
    async def global_leaderboard(self, interaction: discord.Interaction, limit: Optional[int] = 10) -> None:
        safe_limit = max(1, min(limit or 10, 25))
        rows = self.db.get_global_leaderboard(safe_limit)
        if not rows:
            await interaction.response.send_message("No global stats yet.", ephemeral=True)
            return

        lines = [f"Global Stats | Top {safe_limit}"]
        for rank, (user_id, total_broke, guild_count) in enumerate(rows, start=1):
            lines.append(
                f"{rank}. <@{user_id}> | broke meter: {total_broke} | servers: {guild_count}"
            )

        await interaction.response.send_message("\n".join(lines))
