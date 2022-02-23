import discord

import support
from cogs import uno


# non-decorators

async def has_creation_permissions(ctx: discord.ApplicationContext):
    """
    Checks that the bot has all necessary permissions for creating and managing UNO games in the channel. These
    permissions are:

    - View Channel
    - Send Messages
    - Create Public Threads
    - Create Private Threads
    - Send Messages in Threads
    - Manage Messages
    - Manage Threads
    - Embed Links
    - Mention Everyone
    - Use External Emojis

    :param ctx: An ApplicationContext object.
    :return: True if all necessary permissions are granted, False otherwise.
    """

    # this represents the set of all permissions the bot needs. the integer passed into the Permissions constructor is
    # obtained from the Bot Permissions calculator on Discord's Developer Portal: https://discord.com/developers
    expected_permissions = discord.Permissions(395137412096)

    # the actual permissions granted to the bot must be a superset of (i.e. greater than or equal to) the expected
    # permissions
    if ctx.channel.permissions_for(ctx.me).is_superset(expected_permissions):
        return True
    else:
        message = "I don't have the permissions I need to create and manage UNO games in this channel. " \
                  "Make sure I have **all** of the following permissions in this channel, then try again:\n" \
                  "\n" \
                  "- View Channel\n" \
                  "- Send Messages\n" \
                  "- Create Public Threads\n" \
                  "- Create Private Threads\n" \
                  "- Send Messages in Threads\n" \
                  "- Manage Messages\n" \
                  "- Manage Threads\n" \
                  "- Embed Links\n" \
                  "- Mention Everyone\n" \
                  "- Use External Emojis"

        embed = discord.Embed(title="I need more power!", description=message, color=support.ExtendedColors.red())

        await ctx.respond(embed=embed, ephemeral=True)

        return False


# decorators

def verify_uno_context(command):
    """
    A decorator used to check that a command is being used in an UNO game thread before executing its callback.
    """

    async def verify(*args):
        ctx: discord.ApplicationContext = args[1]

        if uno.UnoGame.retrieve_game(ctx.channel_id):
            return await command(*args)
        else:
            message = "You can only use this command in designated UNO game threads. Head to a game thread and " \
                      "try again."
            embed = discord.Embed(title="You can't do that here.", description=message,
                                  color=support.ExtendedColors.red())
            await ctx.respond(embed=embed, ephemeral=True)

    return verify


def verify_uno_player(command):
    """
    A decorator used to check that a command is being used by a player in an UNO game before executing its callback.
    """

    @verify_uno_context
    async def verify(*args):
        ctx: discord.ApplicationContext = args[1]

        game = uno.UnoGame.retrieve_game(ctx.channel_id)

        if any(player for player in game.players.itervalues() if player.user == ctx.user):
            return await command(*args)
        else:
            message = "Only players in this UNO game can use this command."
            embed = discord.Embed(title="That command is for players only.", description=message,
                                  color=support.ExtendedColors.red())
            await ctx.respond(embed=embed, ephemeral=True)

    return verify


def verify_active_game(command):
    """
    A decorator used to check that a command is being used in an UNO game that is currently in progress
    before executing its callback.
    """

    @verify_uno_player
    async def verify(*args):
        ctx: discord.ApplicationContext = args[1]

        game = uno.UnoGame.retrieve_game(ctx.channel_id)

        if not game.is_joinable:
            return await command(*args)
        else:
            message = "You can't use that command until the game has started. Wait until the Game Host starts the " \
                      "game, then try again."
            embed = discord.Embed(title="This game hasn't started yet.", description=message,
                                  color=support.ExtendedColors.red())
            await ctx.respond(embed=embed, ephemeral=True)

    return verify


def verify_player_turn(command):
    """
    A decorator used to check that the player using this command is the one whose turn it currently is before executing
    its callback.
    """

    @verify_active_game
    async def verify(*args):
        ctx: discord.ApplicationContext = args[1]

        game = uno.UnoGame.retrieve_game(ctx.channel_id)

        if game.current_player.value.user == ctx.user:
            return await command(*args)
        else:
            message = "You can only do that when it's your turn. Wait your turn, then try again."
            embed = discord.Embed(title="It's not your turn.", description=message, color=support.ExtendedColors.red())
            await ctx.respond(embed=embed, ephemeral=True)

    return verify


def verify_uno_gamehost(command):
    """
    A decorator used to check that a command is being used by an UNO Game Host before executing its callback..
    """

    @verify_uno_context
    async def verify(*args):
        ctx: discord.ApplicationContext = args[1]

        game = uno.UnoGame.retrieve_game(ctx.channel_id)

        if game.host == ctx.user:
            return await command(*args)
        else:
            message = "Only the Game Host for this UNO game can use that command."
            embed = discord.Embed(title="That command is reserved for the Game Host.", description=message,
                                  color=support.ExtendedColors.red())
            await ctx.respond(embed=embed, ephemeral=True)

    return verify
