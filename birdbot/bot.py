import discord
from discord.ext import commands
import os
from birdbot.database import Database


class BirdBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database()
        testing_guild_id = os.environ.get("TESTING_GUILD_ID")
        self.testing_guild = discord.Object(id=int(testing_guild_id)) if testing_guild_id else None

    async def setup_hook(self):
        await self.load_extension('birdbot.cogs.aggregator')
        if self.testing_guild:
            self.tree.copy_global_to(guild=self.testing_guild)
            await self.tree.sync(guild=self.testing_guild)
        else:
            await self.tree.sync()


