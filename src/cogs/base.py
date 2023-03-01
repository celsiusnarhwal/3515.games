import discord
from attr import define
from discord.ext.commands import Cog as BaseCog


@define
class Cog(BaseCog):
    """
    Base class for cogs.
    """

    bot: discord.Bot
