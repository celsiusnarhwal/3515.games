########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import discord
import inflect as ifl
from discord import Option
from discord.ext import commands
from llist import dllistnode

import shrine
import support
from bot import bot
from cogs import Cog, uno
from support import SlashCommandGroup

inflect = ifl.engine()


@bot.register_cog
class UnoCog(Cog):
    """
    Commands and listeners for UNO.
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
            title="Creating an UNO Game", description=msg, color=support.Color.caution()
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
                color=support.Color.error(),
            )

            await ctx.interaction.edit_original_response(
                embeds=[cancellation_embed], view=None
            )

    # player commands

    @uno_group.command(name="ciao", description="Join or leave an UNO game.")
    @uno.verify_context(level="thread")
    async def ciao(
        self,
        ctx: discord.ApplicationContext,
        action: discord.Option(
            str, "What would you like to do?", choices=["Join Game", "Leave Game"]
        ),
    ):
        options = {
            "Join Game": self.join_game,
            "Leave Game": self.leave_game,
        }

        await options[action](ctx)

    @support.pseudocommand()
    @uno.verify_context(level="thread", is_pseudocommand=True)
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
                color=support.Color.error(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # users can't join games that have already started
        elif not uno_game.is_joinable:
            msg = "You can't join a game that's already in progress."
            embed = discord.Embed(
                title="This game has already started.",
                description=msg,
                color=support.Color.error(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # users can't join games that are already full
        elif not len(uno_game.players) <= uno_game.settings.max_players:
            msg = "You won't be able to join unless someone leaves or is removed by the Game Host."
            embed = discord.Embed(
                title="This game is full.", description=msg, color=support.Color.error()
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, the user is added to the game
        else:
            await uno_game.add_player(ctx, ctx.user)

    @support.pseudocommand()
    @uno.verify_context(level="player", is_pseudocommand=True)
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
                color=support.Color.caution(),
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
        name="play",
        description='Play a card, draw a card, view your hand, make a callout, or say "UNO!".',
    )
    @uno.verify_context(level="player")
    async def play(
        self,
        ctx: discord.ApplicationContext,
        action: discord.Option(
            str,
            "What do you want to do?",
            choices=[
                "Play Card",
                "Draw Card",
                "View Hand",
                "Make Callout",
                'Say "UNO!"',
            ],
        ),
    ):
        options = {
            "Play Card": self.play_card,
            "Draw Card": self.draw_card,
            "View Hand": self.show_hand,
            "Make Callout": self.callout,
            'Say "UNO!"': self.say_uno,
        }

        await options[action](ctx)

    # pseudocommand of play()
    @support.pseudocommand()
    @uno.verify_context(level="game", is_pseudocommand=True)
    async def show_hand(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = uno_game.retrieve_player(ctx.user)

        await player.show_hand(ctx)

    # pseudocommand of play()
    @support.pseudocommand()
    @uno.verify_context(level="turn", is_pseudocommand=True)
    async def play_card(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = uno_game.retrieve_player(ctx.user)

        await player.select_card(ctx)

    # pseudocommand of play()
    @support.pseudocommand()
    @uno.verify_context(level="turn", is_pseudocommand=True)
    async def draw_card(self, ctx: discord.ApplicationContext):

        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = uno_game.retrieve_player(ctx.user)

        await player.draw_card(ctx)

    # pseudocommand of play()
    @support.pseudocommand()
    @uno.verify_context(level="game", is_pseudocommand=True)
    async def say_uno(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = uno_game.retrieve_player(ctx.user)

        if not len(player.hand) == 1:
            msg = "You can only say 'UNO!' when you have one card left."
            embed = discord.Embed(
                title="Get rid of those cards first.",
                description=msg,
                color=support.Color.error(),
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
                color=support.Color.error(),
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
                title="Say UNO?", description=msg, color=support.Color.caution()
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

    # pseudocommand of play()
    @support.pseudocommand()
    @uno.verify_context(level="turn", is_pseudocommand=True)
    async def callout(
        self,
        ctx: discord.ApplicationContext,
    ):
        game: uno.UnoGame = uno.UnoGame.retrieve_game(ctx.channel_id)
        player: uno.UnoPlayer = game.retrieve_player(ctx.user)

        await player.callout(ctx)

    @uno_group.command(name="status", description="Open the UNO Status Center.")
    @uno.verify_context(level="thread")
    async def status(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)

        view = uno.UnoStatusCenterView(ctx=ctx, game=uno_game)
        await view.open_status_center()

    @uno_group.command(
        name="manage", description="Manage an UNO game. Game Hosts only."
    )
    @uno.verify_context(level="thread", verify_host=True)
    async def manage(
        self,
        ctx: discord.ApplicationContext,
        action: Option(
            str,
            "What do you want to do?",
            choices=["Start Game", "End Game", "Kick Player", "Transfer Host Powers"],
        ),
    ):
        options = {
            "Start Game": self.start_game,
            "End Game": self.abort_game,
            "Kick Player": self.kick_player,
            "Transfer Host Powers": self.transfer_host,
        }

        await options[action](ctx)

    # game host commands
    @support.pseudocommand()
    @uno.verify_context(level="thread", verify_host=True, is_pseudocommand=True)
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
                color=support.Color.error(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

        # the host can't start a game that two few players have joined
        elif len(uno_game.players) < uno_game.min_players:
            embed = discord.Embed(
                title="You need more players.",
                description=f"You can't start this game until at least "
                f"{inflect.number_to_words(uno_game.min_players)} players, including "
                "yourself, have joined.",
                color=support.Color.error(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, the host is asked to confirm that they want to start the game
        else:
            embed = discord.Embed(
                title="Start this UNO game?",
                description="Once the game has begun, no new players will be able to join.",
                color=support.Color.caution(),
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

    @support.pseudocommand()
    @uno.verify_context(level="thread", verify_host=True, is_pseudocommand=True)
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
            color=support.Color.caution(),
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

    @support.pseudocommand()
    @uno.verify_context(level="thread", verify_host=True, is_pseudocommand=True)
    async def kick_player(
        self,
        ctx: discord.ApplicationContext,
    ):
        """
        Kick a player from an UNO game.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The invocation context.

        Notes
        -----
        This method is only called upon the invocation of its associated command by the Game Host. Separate faculties
        exist for removing players from games by their own volition (see :meth:`UnoCog.leave_game`) and automatically
        removing players who have been deemed inactive.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = await uno.UnoKickPlayerView(ctx=ctx).present()
        player_node: dllistnode = uno_game.retrieve_player(
            player.user, return_node=True
        )

        await uno_game.kick_player(player_node)

    @support.pseudocommand()
    @uno.verify_context(level="thread", verify_host=True, is_pseudocommand=True)
    async def transfer_host(
        self,
        ctx: discord.ApplicationContext,
    ):
        """
        Transfer host powers to another player.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The invocation context.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = await uno.UnoTransferHostView(ctx=ctx).present()

        await uno_game.transfer_host(player.user)

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
