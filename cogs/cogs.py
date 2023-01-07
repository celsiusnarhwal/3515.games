########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
All of 3515.games' commands and listeners are defined in this module.
"""
import inspect
import sys

import discord
import inflect as ifl
from discord.commands import Option, SlashCommandGroup, slash_command
from discord.ext import commands
from llist import dllistnode

import shrine
import support
from cogs import about, rps, uno, chess, cah

inflect = ifl.engine()


class MasterCog(commands.Cog):
    """
    A subclass of :class:`commands.Cog` that all of 3515.games' cogs inherit from.
    """

    def __init__(self, bot: discord.Bot):
        self.bot = bot


class GeneriCog(MasterCog):
    """
    A cog to contain miscellaneous, standalone, commands that don't fit in any of the other cogs.
    """

    @slash_command(description="Allow me to reintroduce myself.")
    async def about(self, ctx: discord.ApplicationContext):
        await about.AboutView(ctx=ctx).show_about()

    @slash_command(
        description="See which games I have the necessary permissions to play."
    )
    async def caniplay(self, ctx: discord.ApplicationContext):
        games = {
            "Rock-Paper-Scissors": support.GamePermissions.rps(),
            "UNO": support.GamePermissions.uno(),
            "Chess": support.GamePermissions.chess(),
            "Cards Against Humanity": support.GamePermissions.cah(),
        }

        msg = (
            "Each of my games requires a different set of permissions to play. Given the permissions I have in "
            "this channel, here are the games I can and can't play:\n\n"
        )

        for game, permset in games.items():
            msg += f"{game}: {'✅' if ctx.channel.permissions_for(ctx.me) >= permset else '❌'}\n"

        msg += (
            "\nKeep in mind that server moderators can directly control access to my commands via "
            "Server Settings and I have no way of knowing if any of my commands have been disabled on a server "
            "level, so a checkmark here doesn't guarantee that game can actually be played."
        )

        embed = discord.Embed(
            title="Can I play that?", description=msg, color=support.Color.mint()
        )

        await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(
        description="Create a voice channel for a supported game. You won't be able to delete this channel manually."
    )
    async def voice(self, ctx: discord.ApplicationContext):
        supported_games: list[support.HostedMultiplayerGame] = [
            uno.UnoGame,
            cah.CAHGame,
        ]

        for game in supported_games:
            game_obj = game.retrieve_game(ctx.channel_id)
            if game_obj:
                if game_obj.host == ctx.user:
                    channel = await game_obj.create_voice_channel()
                    msg = (
                        f"Your voice channel is {channel.mention}.\n As the Game Host, you can mute and defean the "
                        f"channel's members and even use Priority Speaker. Try it out!\n"
                        f"\n"
                        f"Other players will get access to this channel as soon as they join the game."
                    )

                    embed = discord.Embed(
                        title="Voice channel created!",
                        description=msg,
                        color=support.Color.mint(),
                    )
                    await ctx.respond(embed=embed, ephemeral=True)

                    msg = (
                        f"Players can access {channel.mention} after joining the game."
                    )
                    embed = discord.Embed(
                        title="Voice channel created!",
                        description=msg,
                        color=support.Color.mint(),
                    )

                    await game_obj.thread.send(
                        embed=embed, view=support.GameVoiceURLView(channel)
                    )
                else:
                    msg = "Only the Game Host can create a voice channel for this game."
                    embed = discord.Embed(
                        title="You're not the Game Host.",
                        description=msg,
                        color=support.Color.red(),
                    )

                    await ctx.respond(embed=embed, ephemeral=True)
                break
        else:
            msg = (
                "To create a voice channel, you must use this command in the game thread of a supported game of "
                "which you are the Game Host. Currently, supported games include:\n\n"
            )

            for game in supported_games:
                msg += f"- {game.name}"
                if game is not supported_games[-1]:
                    msg += "\n"

            embed = discord.Embed(
                title="You can't do that here.",
                description=msg,
                color=support.Color.red(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

    @commands.Cog.listener(name="on_guild_channel_delete")
    async def on_guild_channel_delete(self, channel: discord.VoiceChannel):
        if type(channel) == discord.VoiceChannel:
            if (
                channel.category.name.casefold() == "3515.games"
                and len(channel.category.channels) == 0
            ):
                await channel.category.delete()


class RockPaperScissorsCog(MasterCog):
    """
    The cog for the Rock-Paper-Scissors module, which facilitates Rock-Paper-Scissors matches between two members of
    the same Discord server.
    """

    rps_group = SlashCommandGroup("rps", "Commands for playing Rock-Paper-Scissors.")

    @rps_group.command(
        description="Challenge someone to a game of Rock-Paper-Scissors."
    )
    @support.bot_has_permissions(support.GamePermissions.rps())
    async def challenge(
        self,
        ctx: discord.ApplicationContext,
        opponent: Option(discord.User, "Mention a player to be your opponent."),
        game_format: Option(
            str,
            name="format",
            description="Choose whether to play a best-of-three, best-of-five, "
            "or best-of-nine match.",
            choices=["Best of Three", "Best of Five", "Best of Nine"],
        ),
    ):
        """
        Challenge a user to a Rock-Paper-Scissors game between themselves and the command invoker.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The invocation context.
        opponent : discord.User
            The user to challenge to a Rock-Paper-Scissors game.
        game_format : str
            The game format. Must be one of "Best of Three", "Best of Five", or "Best of Nine".
        """
        # the user cannot challenge themselves
        if ctx.user == opponent:
            msg = "You can't play with yourself. Choose someone else to challenge."
            embed = discord.Embed(
                title="Make some friends, please.",
                description=msg,
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # the user cannot challenge the bot
        elif opponent == ctx.me:
            msg = (
                "Unfortunately, my creator is too merciful to allow me to utterly decimate you at "
                "Rock-Paper-Scissors.\n"
                "\n"
                "Challenge someone else."
            )
            embed = discord.Embed(
                title="Not happening.", description=msg, color=support.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # the user cannot challenge other bots
        elif opponent.bot:
            msg = (
                "You can only play with real people. Choose someone else to challenge."
            )
            embed = discord.Embed(
                title="That's a bot.", description=msg, color=support.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)

        else:
            # map game formats to the number of points needed for victory in each
            victory_points = {"Best of Three": 2, "Best of Five": 3, "Best of Nine": 5}

            # create the game object
            rps_game = rps.RPSGame(
                players=[rps.RPSPlayer(ctx.user), rps.RPSPlayer(opponent)],
                game_format=game_format,
                points_to_win=victory_points[game_format],
            )

            challenge_acceptance = await rps_game.issue_challenge(ctx)

            if challenge_acceptance:

                await rps_game.game_intro(ctx)

                while True:
                    move_selection_complete = await rps_game.select_player_moves(ctx)
                    if not move_selection_complete:
                        break
                    else:
                        await rps_game.report_round_results(ctx)

                        match_winner = rps_game.check_for_match_winner()

                        if match_winner:
                            await rps_game.end_match(ctx, match_winner)
                            break
                        else:
                            rps_game.current_round += 1


class UnoCog(MasterCog):
    """
    The cog for the UNO module, which facilitates UNO games with up to 20 members of the same Discord server.
    """

    uno_group = SlashCommandGroup("uno", "Commands for playing UNO.")
    host_group = uno_group.create_subgroup("host", "Commands for UNO Game Hosts.")

    # game creation commands

    @uno_group.command(name="create", description="Create a UNO game.")
    @support.bot_has_permissions(support.GamePermissions.uno())
    @support.invoked_in_text_channel()
    @uno.UnoGame.verify_unique_host()
    async def create_game(
        self,
        ctx: discord.ApplicationContext,
        players: Option(
            int,
            "Choose how many players can join your game (min. 2, max. 20). "
            "This includes you. The default is 20.",
            min_value=2,
            max_value=20,
            default=20,
        ),
        points: Option(
            int,
            "Choose the number of points required to win "
            "(max. 1000). The default is 500.",
            min_value=0,
            max_value=1000,
            default=500,
        ),
        timeout: Option(
            int,
            "Choose how many seconds players must finish their turns in "
            "(min. 30, max. 120). The default is 60.",
            min_value=30,
            max_value=120,
            default=60,
        ),
    ):
        """
        Create an UNO game.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The invocation context.
        players : int
            The maximum number of players that can join the game.
        points
            The number of points required to win the game.
        timeout
            The number of seconds in which players must finish their turns before being penalized.
        """

        # tell the user important information about creating an UNO game
        with shrine.Torii.uno() as torii:
            template = torii.get_template("create-game.md")
            msg = template.render(players=players, points=points, timeout=timeout)

        embed = discord.Embed(
            title="Creating an UNO Game", description=msg, color=support.Color.orange()
        )

        # confirm game creation with user
        view = support.ConfirmationView(ctx=ctx)
        confirmation = await view.request_confirmation(
            prompt_embeds=[embed], ephemeral=True
        )

        if confirmation:
            # create an UnoGame object and associated game thread
            await ctx.interaction.edit_original_response(
                content="Creating your UNO game...", embeds=[], view=None
            )
            game_thread = await ctx.channel.create_thread(
                name=f"UNO with {ctx.user.name} - check pins to play!",
                type=discord.ChannelType.public_thread,
                auto_archive_duration=1440,
            )

            game_settings = uno.UnoGameSettings(
                max_players=players, points_to_win=points, timeout=timeout
            )
            uno_game = uno.UnoGame(
                guild=ctx.guild,
                thread=game_thread,
                host=ctx.user,
                settings=game_settings,
            )
            await uno_game.open_lobby()
            await uno_game.add_player(ctx, ctx.user, is_host=True)

            embed = discord.Embed(
                title="An UNO game has been created!",
                description=f"{ctx.user.mention} created an UNO game! You can "
                f"join the game by typing `/uno join` in the "
                f"game thread.",
                color=support.Color.mint(),
            )

            await ctx.send(
                embed=embed, view=support.GameThreadURLView(thread=game_thread)
            )

            await uno_game.game_timer()

        else:
            cancellation_embed = discord.Embed(
                title="Game Creation Canceled",
                description="You canceled the creation of this UNO game. "
                f"You can create a new game with "
                f"`/{ctx.command.qualified_name}`.",
                color=support.Color.red(),
            )

            await ctx.interaction.edit_original_response(
                embeds=[cancellation_embed], view=None
            )

    # player commands

    @uno_group.command(name="join", description="Join an UNO game.")
    @uno.verify_context(level="thread")
    async def join_game(self, ctx: discord.ApplicationContext):
        """
        Join the invoker to an UNO game.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The invocation context.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)

        # users can't join games they're already in
        if uno_game.retrieve_player(ctx.user):
            msg = (
                "You can't join an UNO game you're already a player in. If you meant to leave, use `/uno leave` "
                "instead."
            )
            embed = discord.Embed(
                title="You're already in this game.",
                description=msg,
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # users can't join games that have already started
        elif not uno_game.is_joinable:
            msg = "You can't join a game that's already in progress."
            embed = discord.Embed(
                title="This game has already started.",
                description=msg,
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # users can't join games that are already full
        elif not len(uno_game.players) <= uno_game.settings.max_players:
            msg = "You won't be able to join unless someone leaves or is removed by the Game Host."
            embed = discord.Embed(
                title="This game is full.", description=msg, color=support.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, the user is added to the game
        else:
            await uno_game.add_player(ctx, ctx.user)

    @uno_group.command(name="leave", description="Leave an UNO game.")
    @uno.verify_context(level="player")
    async def leave_game(self, ctx: discord.ApplicationContext):
        """
        Leave an UNO game on behalf of the invoking player.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The invocation context.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player_node = uno_game.retrieve_player(ctx.user, return_node=True)

        if uno_game and player_node:
            if ctx.user == uno_game.host:
                msg = (
                    "You're the Game Host, so your departure will end the game for everyone else - "
                    "consider transferring your host powers to another player with `/uno host transfer` "
                    "beforehand."
                )
            else:
                if uno_game.is_joinable:
                    msg = "You can rejoin at any time before the game starts."
                else:
                    if len(uno_game.players) - 1 < uno_game.min_players:
                        msg = (
                            "Your departure will leave too few players for the game to continue on, forcing it "
                            "to end for everyone else."
                        )
                    else:
                        msg = "Since the game has already started, you won't be able to rejoin."

            embed = discord.Embed(
                title="Leave this UNO game?",
                description=msg,
                color=support.Color.orange(),
            )

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(
                prompt_embeds=[embed], ephemeral=True
            )

            if confirmation:
                await ctx.interaction.edit_original_response(
                    content="Removing you from the game...", view=None, embeds=[]
                )
                await uno_game.remove_player(player_node=player_node)
            else:
                await ctx.interaction.edit_original_response(
                    content="Okay! You're still in the game!", view=None, embeds=[]
                )

    @uno_group.command(
        name="hand", description="See the UNO cards you're currently holding."
    )
    @uno.verify_context(level="game")
    async def show_hand(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = uno_game.retrieve_player(ctx.user)

        await player.show_hand(ctx)

    @uno_group.command(name="play", description="Play one of your UNO cards.")
    @uno.verify_context(level="turn")
    async def play_card(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = uno_game.retrieve_player(ctx.user)

        await player.select_card(ctx)

    @uno_group.command(name="draw", description="Draw an UNO card.")
    @uno.verify_context(level="turn")
    async def draw_card(self, ctx: discord.ApplicationContext):

        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = uno_game.retrieve_player(ctx.user)

        await player.draw_card(ctx)

    @uno_group.command(
        name="uno", description="Say 'UNO!' when you have one card left."
    )
    @uno.verify_context(level="game")
    async def say_uno(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = uno_game.retrieve_player(ctx.user)

        if not len(player.hand) == 1:
            msg = "You can only say 'UNO!' when you have one card left."
            embed = discord.Embed(
                title="Get rid of those cards first.",
                description=msg,
                color=support.Color.red(),
            )

            await ctx.respond(embed=embed, ephemeral=True)
        elif player.has_said_uno:
            msg = (
                "You've already said UNO. Unless you draw more cards before getting rid of your last one, "
                "you won't be able to say it again."
            )
            embed = discord.Embed(
                title="You did that already.",
                description=msg,
                color=support.Color.red(),
            )

            await ctx.respond(embed=embed, ephemeral=True)
        else:
            msg = (
                "Saying 'UNO!' will notify all other players that you have only one card left. Aside from that, "
                "saying 'UNO!' does nothing else.\n"
                "\n"
                "Say UNO?"
            )
            embed = discord.Embed(
                title="Say UNO?", description=msg, color=support.Color.orange()
            )

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(
                prompt_embeds=[embed], ephemeral=True
            )

            if confirmation:
                await ctx.interaction.edit_original_response(
                    content="Roger that! <:ritsu_salute:727962077888512221>",
                    embeds=[],
                    view=None,
                )
                await player.say_uno()
            else:
                await ctx.interaction.edit_original_response(
                    content="Better hope you don't get called out, then. 😒",
                    embeds=[],
                    view=None,
                )

    @uno_group.command(
        name="callout", description="Call out a player for failing to say 'UNO!'."
    )
    @uno.verify_context(level="turn")
    async def callout(
        self,
        ctx: discord.ApplicationContext,
        receiving_player: Option(
            discord.User, "Mention a player to call out.", name="player"
        ),
    ):

        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player: uno.UnoPlayer = uno_game.retrieve_player(ctx.user)
        recipient: uno.UnoPlayer = uno_game.retrieve_player(receiving_player)

        if not recipient:
            embed = discord.Embed(
                title="That's not a player.",
                description="You can only call out users who are also players in this UNO game.",
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
        elif player == recipient:
            embed = discord.Embed(
                title="Come on, man.",
                description="This should really go without saying, but you can't call out "
                "yourself. Choose another player to call out.",
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            await player.callout(ctx=ctx, recipient=recipient)

    @uno_group.command(name="status", description="Open the UNO Status Center.")
    @uno.verify_context(level="thread")
    async def status(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)

        view = uno.UnoStatusCenterView(ctx=ctx, game=uno_game)
        await view.open_status_center()

    # game host commands
    @host_group.command(name="start", description="Start an UNO game. Game Hosts only.")
    @uno.verify_context(level="thread", verify_host=True)
    async def start_game(self, ctx: discord.ApplicationContext):
        """
        Start an UNO game.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The invocation context.

        Notes
        -----
        This is not to be confused with :meth:`UnoCog.create_game`, which creates games that this method
        may then start.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)

        # the host can't start a game that's already in progress
        if not uno_game.is_joinable:
            embed = discord.Embed(
                title="This game has already started.",
                description="You can't start a game that's already in progress, silly!",
                color=support.Color.red(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

        # the host can't start a game that two few players have joined
        elif len(uno_game.players) < uno_game.min_players:
            embed = discord.Embed(
                title="You need more players.",
                description=f"You can't start this game until at least "
                f"{inflect.number_to_words(uno_game.min_players)} players, including "
                "yourself, have joined.",
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, the host is asked to confirm that they want to start the game
        else:
            embed = discord.Embed(
                title="Start this UNO game?",
                description="Once the game has begun, no new players will be able to join.",
                color=support.Color.orange(),
            )

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(
                prompt_embeds=[embed], ephemeral=True
            )

            if confirmation:
                await ctx.interaction.edit_original_response(
                    content="Let's get started!", embeds=[], view=None
                )
                await uno_game.start_game()

            else:
                await ctx.interaction.edit_original_response(
                    content="Okay! Just use `/uno host start` "
                    "whenever you're ready.",
                    embeds=[],
                    view=None,
                )

    @host_group.command(name="abort", description="Abort an UNO game. Game Hosts only.")
    @uno.verify_context(level="thread", verify_host=True)
    async def abort_game(self, ctx: discord.ApplicationContext):
        """
        Terminate an UNO game.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The invocation context.

        Notes
        -----
        This method is called only upon the invocation of its associated command by the Game Host. Separate faculties
        exist for the normal conclusion of games in which a player has met the win condition and the automatic
        termination of games that can no longer continue.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        message = (
            "Proceeding will immediately end the game and lock the thread for all players, including you.\n"
            "\n"
            "This can't be undone."
        )
        embed = discord.Embed(
            title="Abort this UNO game?",
            description=message,
            color=support.Color.orange(),
        )

        view = support.ConfirmationView(ctx=ctx)
        confirmation = await view.request_confirmation(
            prompt_embeds=[embed], ephemeral=True
        )

        if confirmation:
            await ctx.interaction.edit_original_response(
                content="Aborting your UNO game...", embeds=[], view=None
            )
            await uno_game.force_close(reason="host_abortion")
        else:
            await ctx.interaction.edit_original_response(
                content="Okay! The game is still on.", embeds=[], view=None
            )

    @host_group.command(
        name="kick", description="Kick a player from an UNO game. Game Hosts only."
    )
    @uno.verify_context(level="thread", verify_host=True)
    async def kick_player(
        self,
        ctx: discord.ApplicationContext,
        player: Option(discord.User, "Mention a player to kick."),
    ):
        """
        Kick a player from an UNO game.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The invocation context.
        player : discord.User
            The player to kick.

        Notes
        -----
        This method is only called upon the invocation of its associated command by the Game Host. Separate faculties
        exist for removing players from games by their own volition (see :meth:`UnoCog.leave_game`) and automatically
        removing players who have been deemed inactive.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player_node: dllistnode = uno_game.retrieve_player(player, return_node=True)

        if not player_node:
            embed = discord.Embed(
                title="That's not a player.",
                description="You can't kick someone who isn't a player in this game.",
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
        elif player == ctx.user:
            embed = discord.Embed(
                title="Um, that's you.",
                description="You can't kick yourself. If you want out, use `/uno leave` "
                "(consider transferring your host powers to someone else first, "
                "though).",
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            msg = (
                f"{player.mention} will be able to rejoin the game if it hasn't already started. "
                f"\n"
                f"Kick {player.mention}?"
            )

            embed = discord.Embed(
                title=f"Kick {player.name}?",
                description=msg,
                color=support.Color.orange(),
            )

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(
                prompt_embeds=[embed], ephemeral=True
            )

            if confirmation:
                await ctx.interaction.edit_original_response(
                    content=f"Kicking {player.name}...", embeds=[], view=None
                )
                await uno_game.kick_player(player_node)
            else:
                await ctx.interaction.edit_original_response(
                    content=f"Okay! {player.mention} remains in the game.",
                    embeds=[],
                    view=None,
                )

    @host_group.command(
        name="transfer",
        description="Transfer your Game Host powers to another player. Game Hosts only.",
    )
    @uno.verify_context(level="thread", verify_host=True)
    async def transfer_host(
        self,
        ctx: discord.ApplicationContext,
        player: Option(
            discord.User, "Mention the player you want to transfer host " "powers to."
        ),
    ):

        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)

        # user cannot transfer host powers to themselves
        if player.id == ctx.user.id:
            msg = "Choose another player to transfer host powers to."
            embed = discord.Embed(
                title="You can't transfer host powers to yourself.",
                description=msg,
                color=support.Color.red(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

        # user cannot transfer host powers to non-players
        elif not uno_game.retrieve_player(player):
            msg = "The new Game Host must be a player in this UNO game."
            embed = discord.Embed(
                title="That person's not a player.",
                description=msg,
                color=support.Color.red(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

        # user cannot transfer host powers to players already hosting another game in the same server
        elif uno.UnoGame.find_hosted_games(player, ctx.guild_id):
            msg = "You can't transfer host powers to someone who's already hosting an UNO game in this server."
            embed = discord.Embed(
                title="That player's already hosting a game.",
                description=msg,
                color=support.Color.red(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, the user is asked to confirm the transfer
        else:
            msg = (
                f"{player.mention} will become the Game Host, effective immediately, and all associated powers "
                f"will become exclusively theirs to use. Conversely, you will lose your status as Game Host "
                f"and will no longer be able to use any of the powers that come with the title.\n"
                f"\n"
                f"You will remain a player in this UNO game until it ends or you choose to leave.\n"
                f"\n"
                f"This action cannot be undone.\n"
                f"\n"
                f"Do you want to make {player.name} the Game Host?"
            )

            embed = discord.Embed(
                title=f"Make {player.name} the Game Host?",
                description=msg,
                color=support.Color.orange(),
            )

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(
                prompt_embeds=[embed], ephemeral=True
            )

            if confirmation:
                await ctx.interaction.edit_original_response(
                    content=f"Transferring host powers to {player.mention}...",
                    embeds=[],
                    view=None,
                )
                await uno_game.transfer_host(player)

            else:
                await ctx.interaction.edit_original_response(
                    content="Ok! You're still the Game Host.", embeds=[], view=None
                )

    @commands.Cog.listener()
    async def on_thread_member_remove(self, thread_member: discord.ThreadMember):
        """
        A listener that runs whenever a user is removed from a thread.

        Parameters
        ----------
        thread_member : discord.ThreadMember
            The user that was removed from the thread.

        Notes
        -----
        The purpose of this listener is to enable the automatic removal of UNO players from games when they
        leave associated game threads.
        """
        uno_game = uno.UnoGame.retrieve_game(thread_member.thread_id)
        player_node = uno_game.retrieve_player(thread_member, return_node=True)

        # only call remove_player() if the thread is an UNO game thread AND the user is a player in that game
        if player_node:
            await uno_game.remove_player(player_node=player_node)

    @commands.Cog.listener()
    async def on_raw_thread_delete(self, thread: discord.RawThreadDeleteEvent):
        """
        A listener that runs whenever a thread is deleted.

        Parameters
        ----------
        thread : discord.RawThreadDeleteEvent
            The event of the thread deletion.

        Notes
        -----
        The purpose of this listener is to enable the automatic closure of UNO games whose associated game threads
        are deleted.
        """
        uno_game = uno.UnoGame.retrieve_game(thread.thread_id)

        # only call force_close_thread_deletion() if the deleted thread is associated with an UNO game
        if uno_game:
            await uno_game.force_close(reason="thread_deletion")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.TextChannel):
        """
        A listener that runs whenever a channel is deleted in a server.

        Parameters
        ----------
        channel : discord.abc.GuildChannel
            The channel that was deleted.

        Notes
        -----
        The purpose of this listener is to enable the automatic closure of UNO games whose associated game
        threads' parent channels are deleted.
        """
        # call force_close_channel_deletion() for all channel threads associated with UNO games
        for thread in [
            thread
            for thread in channel.threads
            if thread.id in uno.UnoGame.retrieve_game(thread.id)
        ]:
            uno_game = uno.UnoGame.retrieve_game(thread.id)
            await uno_game.force_close(reason="channel_deletion")


class ChessCog(MasterCog):
    """
    The cog for the chess modules, which facilitates chess games between two members of the same Discord server.
    """

    chess_group = SlashCommandGroup("chess", "Commands for playing chess.")

    @chess_group.command(description="Challenge someone to a game of chess.")
    @support.bot_has_permissions(support.GamePermissions.chess())
    @support.invoked_in_text_channel()
    async def challenge(
        self,
        ctx: discord.ApplicationContext,
        opponent: Option(discord.User, "Mention a user to be your opponent."),
        saving: Option(
            str,
            "Choose whether to enable game saving. Defaults to Enabled.",
            choices=["Enabled", "Disabled"],
            default="Enabled",
        ),
    ):

        saving = True if saving == "Enabled" else False

        if ctx.user == opponent:
            msg = "You can't play with yourself. Choose someone else to challenge."
            embed = discord.Embed(
                title="Make some friends, please.",
                description=msg,
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        elif opponent == ctx.me:
            msg = (
                "Even if my creator allowed me to play with you, I would checkmate you in short order, "
                "because I am better than you at everything.\n"
                "\n"
                "Challenge someone else."
            )
            embed = discord.Embed(
                title="No.", description=msg, color=support.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)

        elif opponent.bot:
            msg = (
                "You can only play with real people. Choose someone else to challenge."
            )
            embed = discord.Embed(
                title="That's a bot.", description=msg, color=support.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)

        elif chess.ChessGame.retrieve_duplicate_game(
            players=[ctx.user, opponent], guild=ctx.guild
        ):
            chess_game = chess.ChessGame.retrieve_duplicate_game(
                players=[ctx.user, opponent], guild=ctx.guild
            )
            msg = (
                f"You're in an ongoing chess match with {opponent.mention} in this server. "
                f"You'll need to wrap it up before you can challenge them to another one."
            )
            embed = discord.Embed(
                title=f"You're already playing with {opponent.name}.",
                description=msg,
                color=support.Color.red(),
            )
            await ctx.respond(
                embed=embed,
                view=support.GameThreadURLView(thread=chess_game.thread),
                ephemeral=True,
            )

        else:
            # confirm with the challenger (i.e. the invoker of /chess challenge) that they want to issue the challenge

            msg = (
                f"You're about to challenge {opponent.mention} to a game of chess. There are a few important "
                f"things you need to know:\n"
                f"\n"
                f"**Chess games are contained within [threads]"
                f"(https://support.discord.com/hc/en-us/articles/4403205878423-Threads-FAQ).** I'll handle the "
                f"creation and management of the thread for you. If you can `Manage Threads`, please refrain from "
                f"editing or deleting the thread until the game is over (trust me, I've got this).\n"
                f"\n"
                f"**Anyone can spectate.** Anyone who can both see and talk in this channel can spectate your "
                f"game. However, only you and your opponent will be able to talk in the game thread.\n"
                f"\n"
                f"**I'm watching for inactivity.** If I determine either you or your opponent to have gone AFK, "
                f"I can forfeit the game on your behalves. Watch out.\n"
                f"\n"
                f"Challenge {opponent.mention} to a game of chess?"
            )

            embed = discord.Embed(
                title="Creating a Chess Game",
                description=msg,
                color=support.Color.orange(),
            )

            view = support.ConfirmationView(ctx=ctx)
            challenge_confirmation = await view.request_confirmation(
                prompt_embeds=[embed], ephemeral=True
            )

            if challenge_confirmation:
                # ask the challenge recipient whether they accept the challenge
                await ctx.interaction.edit_original_response(
                    content=f"Waiting on {opponent.mention}...", embeds=[], view=None
                )

                view = support.GameChallengeResponseView(
                    ctx=ctx,
                    target_user=opponent,
                    challenger=ctx.user,
                    game_name="chess",
                )

                challenge_acceptance = await view.request_response()

                if not challenge_acceptance:
                    return
            else:
                if challenge_confirmation is not None:
                    await ctx.interaction.edit_original_response(
                        content="Okay! Your challenge was canceled.",
                        embeds=[],
                        view=None,
                    )
                    return

            # create a new chess game
            game_thread = await ctx.channel.create_thread(
                name=f"Chess - {ctx.user.name} vs. {opponent.name}",
                type=discord.ChannelType.public_thread,
                auto_archive_duration=1440,
            )

            chess_game = chess.ChessGame(
                thread=game_thread, players=[ctx.user, opponent], saving_enabled=saving
            )

            await chess_game.open_lobby()

            await game_thread.add_user(ctx.user)
            await game_thread.add_user(opponent)

            embed = discord.Embed(
                title="A chess game has begun!",
                description=f"{ctx.user.mention} has challenged {opponent.mention} "
                f"to a game of chess. You can spectate their match by going to the "
                f"game thread.",
                color=support.Color.mint(),
            )

            await ctx.send(
                embed=embed, view=support.GameThreadURLView(thread=chess_game.thread)
            )

            await chess_game.game_timer()

    @chess_group.command(
        description="Identify yourself as ready to begin a chess match."
    )
    @chess.verify_context(level="player")
    async def ready(self, ctx: discord.ApplicationContext):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)

        if player.is_ready:
            msg = "You've already readied yourself with `/chess ready`."
            embed = discord.Embed(
                title="You're already ready.",
                description=msg,
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            msg = (
                "The match will begin as soon as both players are ready. Make sure you really are ready to play; "
                "once you select the Yes button below, you won't be able to change your mind.\n"
                "\n"
                "Identify yourself as ready?"
            )
            embed = discord.Embed(
                title="Ready to play?", description=msg, color=support.Color.orange()
            )

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(
                prompt_embeds=[embed], ephemeral=True
            )

            if confirmation:
                await ctx.interaction.edit_original_response(
                    content=f"You're ready to go. Waiting on "
                    f"{player.opponent.user.mention}...",
                    view=None,
                    embeds=[],
                )
                await player.ready()
            else:
                await ctx.interaction.edit_original_response(
                    content=f"That's cool. Use `/chess ready` whenever you're ready.",
                    view=None,
                    embeds=[],
                )

    @chess_group.command(description="Make a move in a chess match.")
    @chess.verify_context(level="turn")
    async def move(
        self,
        ctx: discord.ApplicationContext,
        notation: Option(
            str,
            name="move",
            description="Specify a move using algebraic or UCI notation. "
            "If you're confused, leave this blank.",
            required=False,
        ),
    ):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)

        if notation:
            await player.move_with_notation(ctx, notation)
        else:
            await player.move_with_gui(ctx)

    @chess_group.command(description="View the board in a chess match.")
    @chess.verify_context(level="game")
    async def board(self, ctx: discord.ApplicationContext):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)

        await player.view_board(ctx)

    @chess_group.command(description="Forfeit a chess match.")
    @chess.verify_context(level="player")
    async def forfeit(self, ctx: discord.ApplicationContext):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)

        if chess_game.has_started:
            msg = (
                f"Forfeiting will cause {player.opponent.user.mention} to be declared the winner. "
                f"If this outcome is not desirable, consider proposing a draw instead.\n"
                "\n"
                "This can't be undone.\n"
                "\n"
                ""
                "Forfeit this match?"
            )
        else:
            msg = (
                "Forfeiting will immediately end the match for both you and your opponent. This can't be undone.\n"
                "\n"
                "Forfeit this match?"
            )

        embed = discord.Embed(
            title="Are you sure?", description=msg, color=support.Color.orange()
        )

        view = support.ConfirmationView(ctx=ctx)

        confirmation = await view.request_confirmation(
            prompt_embeds=[embed], ephemeral=True
        )

        if confirmation:
            await ctx.interaction.edit_original_response(
                content="Forfeiting the match...", view=None, embeds=[]
            )
            await player.forfeit()
        else:
            await ctx.interaction.edit_original_response(
                content=f"Okay! The game is still on.", view=None, embeds=[]
            )

    @chess_group.command(
        description="Propose a draw in a chess match, or rescind a proposal you've already made."
    )
    @chess.verify_context(level="game")
    async def draw(
        self,
        ctx: discord.ApplicationContext,
        mode: Option(
            str,
            description="Choose whether to propose a draw or rescind an existing proposal.",
            choices=["Propose", "Rescind"],
        ),
    ):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)
        if mode == "Propose":
            if player.has_proposed_draw:
                msg = "You'll need to resicind your current proposal before you can make a new one."
                embed = discord.Embed(
                    title="You've already proposed a draw.",
                    description=msg,
                    color=support.Color.red(),
                )
                await ctx.respond(embed=embed, ephemeral=True)
            else:
                msg = (
                    f"If you think it's time to wrap things up, you can propose a draw. If "
                    f"{player.opponent.user.mention} accepts, the match will end in a draw, with neither player "
                    f"being declared the winner.\n"
                    "\n"
                    "If you change your mind before your opponent accepts your proposal, you can rescind your "
                    "proposal by using `/chess draw` and selecting the 'Rescind' option.\n"
                    "\n"
                    "Propose a draw?"
                )

                embed = discord.Embed(
                    title="Proposing a Draw",
                    description=msg,
                    color=support.Color.orange(),
                )

                view = support.ConfirmationView(ctx=ctx)

                confirmation = await view.request_confirmation(
                    prompt_embeds=[embed], ephemeral=True
                )

                if confirmation:
                    await ctx.interaction.edit_original_response(
                        content="Proposing a draw...", view=None, embeds=[]
                    )
                    await player.propose_draw()
                else:
                    await ctx.interaction.edit_original_response(
                        content=f"Okay! You can propose a draw at any time if you change your mind.",
                        view=None,
                        embeds=[],
                    )
        elif mode == "Rescind":
            if not player.has_proposed_draw:
                msg = "You need to propose a draw before you can rescind one."
                embed = discord.Embed(
                    title="You haven't proposed a draw.",
                    description=msg,
                    color=support.Color.red(),
                )

                await ctx.respond(embed=embed, ephemeral=True)
            else:
                await ctx.respond(content="Rescinding your proposal...", ephemeral=True)
                await player.rescind_draw()

    @chess_group.command(description="Revisit your past chess matches.")
    async def replay(self, ctx: discord.ApplicationContext):
        view = chess.ChessReplayMenuView(ctx=ctx)
        await view.initiate_view()

    @commands.Cog.listener(name="on_message")
    async def delete_non_player_messages(self, message: discord.Message):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(message.channel.id)

        if (
            chess_game
            and not chess_game.retrieve_player(message.author)
            and not message.author.bot
            and not support.is_celsius_narhwal(message.author)
        ):
            await message.delete()

    @commands.Cog.listener(name="on_thread_member_remove")
    async def sync_game_thread_removal(self, thread_member: discord.ThreadMember):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(
            thread_member.thread_id
        )
        player: chess.ChessPlayer = chess_game.retrieve_player(thread_member)

        if player:
            await player.forfeit()

            msg = (
                f"I forfeited your chess match against {player.opponent.user.mention} in {chess_game.guild} "
                f"on your behalf because you left the game thread."
            )

            embed = discord.Embed(
                title="Chess Match Forfeited",
                description=msg,
                color=support.Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            await player.user.send(embed=embed)

    @commands.Cog.listener(name="on_raw_thread_delete")
    async def force_close_thread_deletion(self, thread: discord.RawThreadDeleteEvent):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(thread.thread_id)

        if chess_game:
            await chess_game.force_close(reason="thread_deletion")

    @commands.Cog.listener(name="on_guild_channel_delete")
    async def force_close_channel_deletion(self, channel):
        for thread in [
            thread
            for thread in channel.threads
            if chess.ChessGame.retrieve_game(thread.id)
        ]:
            chess_game = chess.ChessGame.retrieve_game(thread.id)
            await chess_game.force_close(reason="channel_deletion")


class CAHCog(MasterCog):
    """
    The cog for the Cards Against Humanity module, which facilitates CAH games between up to 20 members of the same
    Discord server.
    """

    cah_group = SlashCommandGroup(
        "cah", description="Commands for playing Cards Against Humanity."
    )
    host_group = cah_group.create_subgroup(
        "host", description="Commands for CAH Game Hosts."
    )

    @cah_group.command(
        name="create", description="Create a Cards Against Humanity game."
    )
    @support.bot_has_permissions(support.GamePermissions.cah())
    @support.invoked_in_text_channel()
    @cah.CAHGame.verify_unique_host()
    async def create_game(
        self,
        ctx: discord.ApplicationContext,
        players: Option(
            int,
            description="Choose how many players can join your game "
            "(min. 3, max. 20). This includes you. "
            "The default is 20.",
            min_value=3,
            max_value=20,
            default=20,
        ),
        points: Option(
            int,
            description="Choose the number of points required to win "
            "(min 5, max. 100). The default is 10.",
            min_value=5,
            max_value=100,
            default=10,
        ),
        timeout: Option(
            int,
            "Choose how many seconds players must finish their turns in "
            "(min. 30, max. 120). The default is 60.",
            min_value=30,
            max_value=120,
            default=60,
        ),
        voting: Option(
            str,
            description="Choose whether round winners are selected by a "
            "Card Czar or popular vote. The default is Card Czar.",
            choices=["Card Czar", "Popular Vote"],
            default="Card Czar",
        ),
    ):

        msg = (
            "Cards Against Humanity is a pretty vulgar game. You're likely to see content that may gross you out, "
            "offend you, or violate your server's rules. Are you cool with that?"
        )
        embed = discord.Embed(
            title="Content Warning", description=msg, color=support.Color.orange()
        )

        if ctx.user.guild_permissions.manage_guild:
            embed.set_footer(
                text="Whoa, it looks like you're a moderator! Just so you know, you can disable Cards Against Humanity "
                "in this server by changing the permissions for the /cah command in Server Settings > Integrations "
                "> 3515.games."
            )

        view = support.ConfirmationView(ctx=ctx)
        confirmation = await view.request_confirmation(
            prompt_embeds=[embed], ephemeral=True
        )

        if confirmation:
            with shrine.Torii.cah() as torii:
                template = torii.get_template("create-game.md")
                msg = template.render(
                    max_players=players, points=points, timeout=timeout
                )

            embed = discord.Embed(
                title="Creating a Cards Against Humanity Game",
                description=msg,
                color=discord.Color.orange(),
            )

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(
                prompt_embeds=[embed], edit=True
            )

            if confirmation:
                cards = await cah.PackSelectView(ctx=ctx).get_packs()

                if not cards:
                    return

                game_thread = await ctx.channel.create_thread(
                    name=f"CAH with {ctx.user.name} - check pins to play!",
                    type=discord.ChannelType.public_thread,
                    auto_archive_duration=1440,
                )

                game_settings = cah.CAHGameSettings(
                    max_players=players,
                    points_to_win=points,
                    timeout=timeout,
                    use_czar=bool(voting == "Card Czar"),
                )

                game_class = (
                    cah.CAHGame if game_settings.use_czar else cah.CAHPopularVoteGame
                )
                cah_game = game_class(
                    guild=ctx.guild,
                    thread=game_thread,
                    host=ctx.user,
                    cards=cards,
                    settings=game_settings,
                )

                await cah_game.open_lobby()
                await cah_game.add_player(ctx=ctx, user=ctx.user, is_host=True)

                msg = (
                    f"{ctx.user.mention} created a Cards Against Humanity game! You can join the game by typing "
                    f"`/cah join` in the game thread."
                )
                embed = discord.Embed(
                    title="A Cards Against Humanity game has been created!",
                    description=msg,
                    color=support.Color.mint(),
                )

                await ctx.send(
                    embed=embed, view=support.GameThreadURLView(thread=game_thread)
                )
            else:
                msg = (
                    f"You canceled the creation of this Cards Against Humanity game. You can create a new game "
                    f"with `/{ctx.command.qualified_name}`."
                )
                embed = discord.Embed(
                    title="Game Creation Canceled",
                    description=msg,
                    color=support.Color.red(),
                )
                await ctx.interaction.edit_original_response(embeds=[embed], view=None)
        else:
            msg = (
                f"You canceled the creation of this Cards Against Humanity game. You can create a new game with "
                f"`/{ctx.command.qualified_name}`."
            )
            embed = discord.Embed(
                title="Game Creation Canceled",
                description=msg,
                color=support.Color.red(),
            )
            await ctx.interaction.edit_original_response(embeds=[embed], view=None)

    @cah_group.command(name="join", description="Join a Cards Against Humanity game.")
    @cah.verify_context(level="thread")
    async def join_game(self, ctx: discord.ApplicationContext):
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)

        # users can't join games they're already in
        if cah_game.retrieve_player(ctx.user):
            msg = (
                "You can't join an CAH game you're already a player in. If you meant to leave, use `/cah leave` "
                "instead."
            )
            embed = discord.Embed(
                title="You're already in this game.",
                description=msg,
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # users can't join games that have already started
        elif not cah_game.is_joinable:
            msg = "You can't join a game that's already in progress."
            embed = discord.Embed(
                title="This game has already started.",
                description=msg,
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # users can't join games that are already full
        elif not len(cah_game.players) <= cah_game.settings.max_players:
            msg = "You won't be able to join unless someone leaves or is removed by the Game Host."
            embed = discord.Embed(
                title="This game is full.", description=msg, color=support.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)

        else:
            await cah_game.add_player(ctx=ctx, user=ctx.user)

    @cah_group.command(name="leave", description="Leave a Cards Against Humanity game.")
    @cah.verify_context(level="player")
    async def leave_game(self, ctx: discord.ApplicationContext):
        """
        Voluntarily removes the player from an CAH game. Can only be used in CAH game threads.

        :param ctx: An ApplicationContext object.
        """
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)
        player_node = cah_game.retrieve_player(ctx.user, return_node=True)

        if cah_game and player_node:
            if ctx.user == cah_game.host:
                msg = (
                    "You're the Game Host, so your departure will end the game for everyone else - "
                    "consider transferring your host powers to another player with `/cah host transfer` "
                    "beforehand."
                )
            else:
                if cah_game.is_joinable:
                    msg = "You can rejoin at any time before the game starts."
                else:
                    if len(cah_game.players) - 1 < cah_game.min_players:
                        msg = (
                            "Your departure will leave too few players for the game to continue on, forcing it "
                            "to end for everyone else."
                        )
                    else:
                        msg = "Since the game has already started, you won't be able to rejoin."

            embed = discord.Embed(
                title="Leave this Cards Against Humanity game?",
                description=msg,
                color=support.Color.orange(),
            )

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(
                prompt_embeds=[embed], ephemeral=True
            )

            if confirmation:
                await ctx.interaction.edit_original_response(
                    content="Removing you from the game...", view=None, embeds=[]
                )
                await cah_game.remove_player(player_node=player_node)
            else:
                await ctx.interaction.edit_original_response(
                    content="Okay! You're still in the game!", view=None, embeds=[]
                )

    @cah_group.command(
        name="hand", description="See the white cards you're currently holding."
    )
    @cah.verify_context(level="game")
    async def show_hand(self, ctx: discord.ApplicationContext):
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)
        player = cah_game.retrieve_player(ctx.user)

        await player.show_hand(ctx)

    @cah_group.command(name="play", description="Play a white card (or two).")
    @cah.verify_context(level="turn")
    async def play_card(self, ctx: discord.ApplicationContext):
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)
        player = cah_game.retrieve_player(ctx.user)

        await player.pick_cards(ctx)

    @cah_group.command(name="vote", description="Vote for the funniest submission.")
    @cah.verify_context(level="turn")
    async def vote(self, ctx: discord.ApplicationContext):
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)
        player = cah_game.retrieve_player(ctx.user)

        await player.vote(ctx)

    @cah_group.command(name="status", description="Open the CAH Status Center.")
    async def status(self, ctx: discord.ApplicationContext):
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)

        await cah.CAHStatusCenterView(ctx=ctx, game=cah_game).open_status_center()

    @host_group.command(
        name="start",
        description="Start an Cards Against Humanity game. Game Hosts only.",
    )
    @cah.verify_context(level="thread", verify_host=True)
    async def start_game(self, ctx: discord.ApplicationContext):
        """
        Starts an CAH game that has already been created and which at least one player aside from the Game Host has
        joined. Can only be used by CAH Game Hosts in CAH game threads. Not to be confused with
        ``create_public_game()`` and ``create_private_game()``, which create CAH games that must later be started with
        this command.

        :param ctx: An ApplicationContext object.
        """
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)

        # the host can't start a game that's already in progress
        if not cah_game.is_joinable:
            embed = discord.Embed(
                title="This game has already started.",
                description="You can't start a game that's already in progress, silly!",
                color=support.Color.red(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

        # the host can't start a game that too few players have joined
        elif len(cah_game.players) < cah_game.min_players:
            embed = discord.Embed(
                title="You need more players.",
                description=f"You can't start this game until at least "
                f"{inflect.number_to_words(cah_game.min_players)} players, including "
                "yourself, have joined.",
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, the host is asked to confirm that they want to start the game
        else:
            embed = discord.Embed(
                title="Start this Cards Against Humanity game?",
                description="Once the game has begun, no new players will be able to join.",
                color=support.Color.orange(),
            )

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(
                prompt_embeds=[embed], ephemeral=True
            )

            if confirmation:
                await ctx.interaction.edit_original_response(
                    content="Let's get started!", embeds=[], view=None
                )
                await cah_game.start_game()

            else:
                await ctx.interaction.edit_original_response(
                    content="Okay! Just use `/cah host start` "
                    "whenever you're ready.",
                    embeds=[],
                    view=None,
                )

    @host_group.command(name="abort", description="Abort a CAH game. Game Hosts only.")
    @cah.verify_context(level="thread", verify_host=True)
    async def abort_game(self, ctx: discord.ApplicationContext):
        """
        Aborts an ongoing CAH game, forcefully ending it for all players. Can only be used by CAH Game Hosts in CAH game
        threads.

        :param ctx: An ApplicationContext object.
        """
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)
        message = (
            "Proceeding will immediately end the game and lock the thread for all players, including you.\n"
            "\n"
            "This can't be undone."
        )
        embed = discord.Embed(
            title="Abort this CAH game?",
            description=message,
            color=support.Color.orange(),
        )

        view = support.ConfirmationView(ctx=ctx)
        confirmation = await view.request_confirmation(
            prompt_embeds=[embed], ephemeral=True
        )

        if confirmation:
            await ctx.interaction.edit_original_response(
                content="Aborting your CAH game...", embeds=[], view=None
            )
            await cah_game.force_close(reason="host_abortion")
        else:
            await ctx.interaction.edit_original_response(
                content="Okay! The game is still on.", embeds=[], view=None
            )

    @host_group.command(
        name="kick",
        description="Kick a player from a Cards Against Humanity game. Game Hosts only.",
    )
    @cah.verify_context(level="thread", verify_host=True)
    async def kick_player(
        self, ctx: discord.ApplicationContext, player: discord.Member
    ):
        """
        Kicks a player from an CAH game. Can only be used by CAH Game Hosts in CAH game threads.

        :param player: The player to kick.
        :param ctx: An ApplicationContext object.
        """
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)
        player_node: dllistnode = cah_game.retrieve_player(player, return_node=True)

        if not player_node:
            embed = discord.Embed(
                title="That's not a player.",
                description="You can't kick someone who isn't a player in this game.",
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
        elif player == ctx.user:
            embed = discord.Embed(
                title="Um, that's you.",
                description="You can't kick yourself. If you want out, use `/cah leave` "
                "(consider transferring your host powers to someone else first, "
                "though).",
                color=support.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            if cah_game.is_joinable:
                msg = (
                    f"{player.mention} will be able to rejoin the game at any time before it starts.\n"
                    f"\n"
                    f"Kick {player.mention}?"
                )
            elif len(cah_game.players) - 1 < cah_game.min_players:
                msg = (
                    f"Kicking {player.mention} will leave too few players for the game to continue on, forcing it "
                    f"to end.\n"
                    f"\n"
                    f"Kick {player.mention}?"
                )
            else:
                msg = (
                    f"{player.mention} will be removed from the game.\n"
                    f"\n"
                    f"Kick {player.mention}?"
                )

            embed = discord.Embed(
                title=f"Kick {player.name}?",
                description=msg,
                color=support.Color.orange(),
            )

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(
                prompt_embeds=[embed], ephemeral=True
            )

            if confirmation:
                await ctx.interaction.edit_original_response(
                    content=f"Kicking {player.name}...", embeds=[], view=None
                )
                await cah_game.kick_player(player_node)
            else:
                await ctx.interaction.edit_original_response(
                    content=f"Okay! {player.mention} remains in the game.",
                    embeds=[],
                    view=None,
                )

    @host_group.command(
        name="transfer",
        description="Transfer your Game Host powers to another player. Game Hosts only.",
    )
    @cah.verify_context(level="thread", verify_host=True)
    async def transfer_host(
        self,
        ctx: discord.ApplicationContext,
        player: Option(
            discord.User, "Mention the player you want to transfer host " "powers to."
        ),
    ):

        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)

        # user cannot transfer host powers to themselves
        if player.id == ctx.user.id:
            msg = "Choose another player to transfer host powers to."
            embed = discord.Embed(
                title="You can't transfer host powers to yourself.",
                description=msg,
                color=support.Color.red(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

        # user cannot transfer host powers to non-players
        elif not cah_game.retrieve_player(player):
            msg = "The new Game Host must be a player in this UNO game."
            embed = discord.Embed(
                title="That person's not a player.",
                description=msg,
                color=support.Color.red(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

        # user cannot transfer host powers to players already hosting another game in the same server
        elif uno.UnoGame.find_hosted_games(player, ctx.guild_id):
            msg = "You can't transfer host powers to someone who's already hosting an CAH game in this server."
            embed = discord.Embed(
                title="That player's already hosting a game.",
                description=msg,
                color=support.Color.red(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, the user is asked to confirm the transfer
        else:
            msg = (
                f"{player.mention} will become the Game Host, effective immediately, and all associated powers "
                f"will become exclusively theirs to use. Conversely, you will lose your status as Game Host "
                f"and will no longer be able to use any of the powers that come with the title.\n"
                f"\n"
                f"You will remain a player in this CAH game until it ends or you choose to leave.\n"
                f"\n"
                f"This action cannot be undone.\n"
                f"\n"
                f"Do you want to make {player.name} the Game Host?"
            )

            embed = discord.Embed(
                title=f"Make {player.name} the Game Host?",
                description=msg,
                color=support.Color.orange(),
            )

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(
                prompt_embeds=[embed], ephemeral=True
            )

            if confirmation:
                await ctx.interaction.edit_original_response(
                    content=f"Transferring host powers to {player.mention}...",
                    embeds=[],
                    view=None,
                )
                await cah_game.transfer_host(player)

            else:
                await ctx.interaction.edit_original_response(
                    content="Ok! You're still the Game Host.", embeds=[], view=None
                )

    @commands.Cog.listener(name="on_thread_member_remove")
    async def on_thread_member_remove(self, thread_member: discord.ThreadMember):
        """
        A listener that runs whenever a user is removed from a thread. This runs whenever *any* user is removed from
        *any* thread in the server, regardless of whether they're playing an CAH game or being removed from an CAH game
        thread. The purpose of this listener is to enable the automatic removal of CAH players from games when they
        leave associated game threads.

        :param thread_member: A discord.ThreadMember object representing the removed user.
        """
        cah_game = cah.CAHGame.retrieve_game(thread_member.thread_id)
        player_node = cah_game.retrieve_player(thread_member, return_node=True)

        # only call remove_player() if the thread is an CAH game thread AND the user is a player in that game
        if player_node:
            await cah_game.remove_player(player_node=player_node)

    @commands.Cog.listener(name="on_raw_thread_delete")
    async def on_raw_thread_delete(self, thread: discord.RawThreadDeleteEvent):
        cah_game: cah.CAHGame = cah.CAHGame.retrieve_game(thread.thread_id)
        if cah_game:
            await cah_game.force_close(reason="thread_deletion")

    @commands.Cog.listener(name="on_guild_channel_delete")
    async def on_guild_channel_delete(self, channel: discord.TextChannel):
        for thread in [thread for thread in channel.threads]:
            cah_game = cah.CAHGame.retrieve_game(thread.id)
            if cah_game:
                await cah_game.force_close(reason="channel_deletion")


all_cogs = [
    cog
    for _, cog in inspect.getmembers(sys.modules[__name__], inspect.isclass)
    if issubclass(cog, MasterCog)
]
