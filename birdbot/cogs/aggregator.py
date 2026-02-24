import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
import os

from birdbot.database import Database

import pandas as pd

def get_time_of_day(hour: int) -> str:
    if 5 <= hour < 10:
        return "Morning"
    elif 10 <= hour < 14:
        return "Mid-day"
    elif 14 <= hour < 18:
        return "Afternoon"
    elif 18 <= hour < 21:
        return "Evening"
    else:
        return "Night"

def get_am_pm(hour: int) -> str:
    if hour < 12:
        return "AM"
    else:
        return "PM"

def split_message(message: str, max_length: int = 2000) -> list[str]:
    lines = message.splitlines(keepends=True)
    chunks = []
    current_chunk = ""

    for line in lines:
        if len(current_chunk) + len(line) > max_length:
            chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += line

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def build_aggregate_report(db: Database) -> str:
    min_observations = 1
    min_confidence = 0.6

    df = db.get_recent_observations()
    print(f"[report] total rows from DB: {len(df)}", flush=True)

    df = df[df['confidence'] >= min_confidence]
    print(f"[report] rows after confidence filter (>={min_confidence}): {len(df)}", flush=True)

    df['time_of_day'] = df['begin_time'].dt.hour.map(get_time_of_day)
    time_order = ['Morning', 'Mid-day', 'Afternoon', 'Evening', 'Night']

    grouped = df.groupby(['source_node', 'common_name', 'scientific_name']).agg(
        observations=('id', 'count'),
        avg_confidence=('confidence', 'mean'),
        times_seen = ('time_of_day', lambda x: sorted(set(x.dropna()), key=time_order.index))
    ).reset_index()

    grouped = grouped[grouped['observations'] >= min_observations]
    print(f"[report] species groups after min_observations filter (>={min_observations}): {len(grouped)}", flush=True)

    grouped = grouped.sort_values(
        by=['source_node', 'observations'],
        ascending=[False, False]
    )

    lines = ['>>> # 🐦 Daily BirdNET report']

    for source_node in grouped['source_node'].unique():
        lines.append(f"## Node: `{source_node}`")
        source_data = grouped[grouped['source_node'] == source_node]

        for _, row in source_data.iterrows():
            lines.append(
                f"**{row['common_name']}** (*{row['scientific_name']}*)\n"
                f"-#\t`n={row['observations']}` `conf={round(row['avg_confidence'] * 100):d}%`"
                f" `seen: {', '.join(row['times_seen'])}`\n"
            )

    return '\n'.join(lines)


async def send_daily_aggregate(bot: discord.Client, db: Database) -> None:
    message = build_aggregate_report(db)
    channel = bot.get_channel(int(os.environ.get("UPDATE_CHANNEL_ID")))
    for chunk in split_message(message):
        await channel.send(chunk)


class AggregatorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db
        self._scheduler_task: asyncio.Task | None = None

    async def cog_load(self):
        self._scheduler_task = asyncio.create_task(self._aggregate_scheduler())

    async def cog_unload(self):
        if self._scheduler_task:
            self._scheduler_task.cancel()

    async def _aggregate_scheduler(self):
        await self.bot.wait_until_ready()
        while True:
            now = datetime.datetime.now()
            target = now.replace(hour=22, minute=0, second=0, microsecond=0)
            if now >= target:
                target += datetime.timedelta(days=1)
            await asyncio.sleep((target - now).total_seconds())

            await send_daily_aggregate(self.bot, self.db)

    @app_commands.command(name="report", description="Post the daily BirdNET report immediately")
    async def report_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        message = build_aggregate_report(self.db)
        chunks = split_message(message)
        await interaction.followup.send(chunks[0])
        for chunk in chunks[1:]:
            await interaction.channel.send(chunk)


async def setup(bot: commands.Bot):
    await bot.add_cog(AggregatorCog(bot))
