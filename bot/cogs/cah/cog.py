########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import discord
import inflect as ifl
from cogs import Cog, cah
from discord import Option
from discord.ext import commands
from llist import dllistnode

import shrine
import support
from bot import bot
from support import SlashCommandGroup

inflect = ifl.engine()


@bot.register_cog
class CAHCog(Cog):
    """
    Commands and listeners for Cards Against Humanity.
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
    @support.not_in_maintenance()
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
            title="Content Warning", description=msg, color=support.Color.caution()
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
                    max_players=players, points=points, timeout=timeout, voting=voting
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
                deck = await cah.CAHPackSelectView(ctx=ctx).get_packs()

                if not deck:
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

                cah_game = cah.CAHGame(
                    guild=ctx.guild,
                    thread=game_thread,
                    host=ctx.user,
                    deck=deck,
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
                    color=support.Color.error(),
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
                color=support.Color.error(),
            )
            await ctx.interaction.edit_original_response(embeds=[embed], view=None)

    @cah_group.command(
        name="ciao", description="Join or leave an Cards Against Humanity game."
    )
    @cah.verify_context(level="thread")
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

    # pseudocommand of ciao()
    @support.pseudocommand()
    @cah.verify_context(level="thread")
    async def join_game(self, ctx: discord.ApplicationContext):
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)

        # users can't join games they're already in
        if cah_game.retrieve_player(ctx.user):
            msg = (
                "You can't join an CAH game you're already a player in. If you meant to leave, use "
                "`/cah ciao > Leave Game` instead."
            )
            embed = discord.Embed(
                title="You're already in this game.",
                description=msg,
                color=support.Color.error(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # users can't join games that have already started
        elif not cah_game.is_joinable:
            msg = "You can't join a game that's already in progress."
            embed = discord.Embed(
                title="This game has already started.",
                description=msg,
                color=support.Color.error(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # users can't join games that are already full
        elif not len(cah_game.players) <= cah_game.settings.max_players:
            msg = "You won't be able to join unless someone leaves or is removed by the Game Host."
            embed = discord.Embed(
                title="This game is full.", description=msg, color=support.Color.error()
            )
            await ctx.respond(embed=embed, ephemeral=True)

        else:
            await cah_game.add_player(ctx=ctx, user=ctx.user)

    # pseudocommand of ciao()
    @support.pseudocommand()
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
                    "consider transferring your host powers to another player with `/cah manage > "
                    "Transfer Host Powers` beforehand."
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

    @cah_group.command(
        name="play", description="Play white cards or vote for a submission."
    )
    @cah.verify_context(level="turn")
    async def play_card(self, ctx: discord.ApplicationContext):
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)
        player = cah_game.retrieve_player(ctx.user)

        if cah_game.is_voting:
            await player.vote(ctx)
        else:
            await player.pick_cards(ctx)

    @cah_group.command(name="status", description="Open the CAH Status Center.")
    async def status(self, ctx: discord.ApplicationContext):
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)

        await cah.CAHStatusCenterView(ctx=ctx, game=cah_game).open_status_center()

    @cah_group.command(
        name="manage",
        description="Manage an Cards Against Humanity game. Game Hosts only.",
    )
    @cah.verify_context(level="thread", verify_host=True)
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

    # pseudocommand of manage()
    @support.pseudocommand()
    @cah.verify_context(level="thread", verify_host=True)
    async def start_game(self, ctx: discord.ApplicationContext):
        """
        Start an UNO game.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The invocation context.

        Notes
        -----
        This is not to be confused with :meth:`CAHCog.create_game`, which creates games that this method
        may then start.
        """
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)

        # the host can't start a game that's already in progress
        if not cah_game.is_joinable:
            embed = discord.Embed(
                title="This game has already started.",
                description="You can't start a game that's already in progress, silly!",
                color=support.Color.error(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

        # the host can't start a game that too few players have joined
        elif (
            len(cah_game.players) < cah_game.min_players
            and ctx.guild_id != support.TESTING_GROUNDS
        ):
            embed = discord.Embed(
                title="You need more players.",
                description=f"You can't start this game until at least "
                f"{inflect.number_to_words(cah_game.min_players)} players, including "
                "yourself, have joined.",
                color=support.Color.error(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, the host is asked to confirm that they want to start the game
        else:
            embed = discord.Embed(
                title="Start this Cards Against Humanity game?",
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
                await cah_game.start_game()

            else:
                await ctx.interaction.edit_original_response(
                    content="Okay! Just use `/cah host start` "
                    "whenever you're ready.",
                    embeds=[],
                    view=None,
                )

    # pseudocommand of manage()
    @support.pseudocommand()
    @cah.verify_context(level="thread", verify_host=True)
    async def abort_game(self, ctx: discord.ApplicationContext):
        """
        Abort an UNO game.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The invocation context.
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
            color=support.Color.caution(),
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

    # pseudocommand of manage()
    @support.pseudocommand()
    @cah.verify_context(level="thread", verify_host=True)
    async def kick_player(self, ctx: discord.ApplicationContext):
        """
        Kick a player from an CAH game.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The invocation context.
        """
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)
        player = await cah.CAHKickPlayerView(ctx=ctx).present()
        player_node: dllistnode = cah_game.retrieve_player(
            player.user, return_node=True
        )

        await cah_game.kick_player(player_node)

    # pseudocommand of manage()
    @support.pseudocommand()
    @cah.verify_context(level="thread", verify_host=True)
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
        cah_game = cah.CAHGame.retrieve_game(ctx.channel_id)
        player = await cah.CAHTransferHostView(ctx=ctx).present()

        await cah_game.transfer_host(player.user)

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
