import math

import discord
from discord import app_commands
from discord.ext import commands

from smoke_alarm.database import StatsDatabase


ACCENT_RED_COLOR = discord.Color.from_rgb(222, 49, 57)
PAGE_SIZE = 10


def _build_local_embed(
    rows: list[tuple[int, int]],
    page: int,
    total_count: int,
) -> discord.Embed:
    total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
    start_rank = (page - 1) * PAGE_SIZE + 1
    lines = []
    for index, (user_id, broke_meter) in enumerate(rows):
        rank = start_rank + index
        lines.append(f"**#{rank}** <@{user_id}>  |  broke meter: **{broke_meter}**")

    embed = discord.Embed(
        title="Local Leaderboard",
        description="\n".join(lines) if lines else "No local stats yet for this server.",
        color=ACCENT_RED_COLOR,
    )
    embed.set_footer(text=f"Page {page}/{total_pages} | 10 per page")
    return embed


def _build_global_embed(
    rows: list[tuple[int, int, int]],
    page: int,
    total_count: int,
) -> discord.Embed:
    total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
    start_rank = (page - 1) * PAGE_SIZE + 1
    lines = []
    for index, (user_id, total_broke, guild_count) in enumerate(rows):
        rank = start_rank + index
        lines.append(
            f"**#{rank}** <@{user_id}>  |  broke meter: **{total_broke}**  |  servers: **{guild_count}**"
        )

    embed = discord.Embed(
        title="Global Leaderboard",
        description="\n".join(lines) if lines else "No global stats yet.",
        color=ACCENT_RED_COLOR,
    )
    embed.set_footer(text=f"Page {page}/{total_pages} | 10 per page")
    return embed


class LeaderboardPager(discord.ui.View):
    def __init__(
        self,
        db: StatsDatabase,
        author_id: int,
        is_global: bool,
        guild_id: int | None,
        total_count: int,
    ) -> None:
        super().__init__(timeout=180)
        self.db = db
        self.author_id = author_id
        self.is_global = is_global
        self.guild_id = guild_id
        self.total_count = total_count
        self.page = 1
        self.total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.previous_button.disabled = self.page <= 1
        self.next_button.disabled = self.page >= self.total_pages

    def _load_embed_for_page(self) -> discord.Embed:
        offset = (self.page - 1) * PAGE_SIZE
        if self.is_global:
            rows = self.db.get_global_leaderboard_page(PAGE_SIZE, offset)
            return _build_global_embed(rows, self.page, self.total_count)

        if self.guild_id is None:
            return discord.Embed(
                title="Local Leaderboard",
                description="This command can only be used in a server.",
                color=ACCENT_RED_COLOR,
            )

        rows = self.db.get_server_leaderboard_page(self.guild_id, PAGE_SIZE, offset)
        return _build_local_embed(rows, self.page, self.total_count)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the command user can switch leaderboard pages.",
                ephemeral=True,
            )
            return False
        return True

    async def _refresh_message(self, interaction: discord.Interaction) -> None:
        self._update_buttons()
        embed = self._load_embed_for_page()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="<-", style=discord.ButtonStyle.secondary)
    async def previous_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        if self.page > 1:
            self.page -= 1
        await self._refresh_message(interaction)

    @discord.ui.button(label="->", style=discord.ButtonStyle.danger)
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        if self.page < self.total_pages:
            self.page += 1
        await self._refresh_message(interaction)

    async def on_timeout(self) -> None:
        self.previous_button.disabled = True
        self.next_button.disabled = True


class LeaderboardCog(commands.Cog):
    def __init__(self, db: StatsDatabase) -> None:
        self.db = db

    @app_commands.command(name="localstats", description="Show local leaderboard stats with page controls")
    async def local_stats(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        total_count = self.db.get_server_leaderboard_count(interaction.guild_id)
        if total_count == 0:
            await interaction.response.send_message(
                "No local stats yet for this server.", ephemeral=True
            )
            return

        view = LeaderboardPager(
            db=self.db,
            author_id=interaction.user.id,
            is_global=False,
            guild_id=interaction.guild_id,
            total_count=total_count,
        )
        embed = view._load_embed_for_page()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="globalstats", description="Show global leaderboard stats with page controls")
    async def global_leaderboard(self, interaction: discord.Interaction) -> None:
        total_count = self.db.get_global_leaderboard_count()
        if total_count == 0:
            await interaction.response.send_message("No global stats yet.", ephemeral=True)
            return

        view = LeaderboardPager(
            db=self.db,
            author_id=interaction.user.id,
            is_global=True,
            guild_id=None,
            total_count=total_count,
        )
        embed = view._load_embed_for_page()
        await interaction.response.send_message(embed=embed, view=view)
