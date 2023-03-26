########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import discord
from cogs import chess
from cogs.base import Cog
from discord import Option
from discord.ext import commands

import support
from bot import bot
from support import SlashCommandGroup


@bot.register_cog
class ChessCog(Cog):
    """
    Commands and listeners for chess.
    """

    chess_group = SlashCommandGroup("chess", "Commands for playing chess.")

    @chess_group.command()
    @support.not_in_maintenance()
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
        """
        Challenge someone to a game of chess.
        """

        saving = True if saving == "Enabled" else False

        if ctx.user == opponent:
            msg = "You can't play with yourself. Choose someone else to challenge."
            embed = discord.Embed(
                title="Make some friends, please.",
                description=msg,
                color=support.Color.error(),
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
                title="No.", description=msg, color=support.Color.error()
            )
            await ctx.respond(embed=embed, ephemeral=True)

        elif opponent.bot:
            msg = (
                "You can only play with real people. Choose someone else to challenge."
            )
            embed = discord.Embed(
                title="That's a bot.", description=msg, color=support.Color.error()
            )
            await ctx.respond(embed=embed, ephemeral=True)

        elif chess.ChessGame.retrieve_duplicate_game(
            players=[ctx.user, opponent], guild=ctx.guild
        ):
            chess_game = chess.ChessGame.retrieve_duplicate_game(
                players=[ctx.user, opponent], guild=ctx.guild
            )
            msg = (
                f"You're in an ongoing chess game with {opponent.mention} in this server. "
                f"You'll need to wrap it up before you can challenge them to another one."
            )
            embed = discord.Embed(
                title=f"You're already playing with {opponent.name}.",
                description=msg,
                color=support.Color.error(),
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
                color=support.Color.caution(),
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
                guild=ctx.guild,
                thread=game_thread,
                players=[ctx.user, opponent],
                saving_enabled=saving,
            )

            await chess_game.open_lobby()

            await game_thread.add_user(ctx.user)
            await game_thread.add_user(opponent)

            embed = discord.Embed(
                title="A chess game has begun!",
                description=f"{ctx.user.mention} has challenged {opponent.mention} "
                f"to a game of chess! You can spectate their game by going to the "
                f"game thread.",
                color=support.Color.mint(),
            )

            await ctx.send(
                embed=embed, view=support.GameThreadURLView(thread=chess_game.thread)
            )

            await chess_game.game_timer()

    @chess_group.command()
    @chess.verify_context(level="player")
    async def ready(self, ctx: discord.ApplicationContext):
        """
        Ready yourself to begin a chess game.
        """
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)

        if player.is_ready:
            msg = "You've already readied yourself with `/chess ready`."
            embed = discord.Embed(
                title="You're already ready.",
                description=msg,
                color=support.Color.error(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            msg = (
                "The game will begin as soon as both players are ready. Make sure you really are ready to play; "
                "once you select the Yes button below, you won't be able to change your mind.\n"
                "\n"
                "Are you ready to play?"
            )
            embed = discord.Embed(
                title="Ready to play?", description=msg, color=support.Color.caution()
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

    @chess_group.command()
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
        """
        Make a move.
        """
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)

        if notation:
            await player.move_with_notation(ctx, notation)
        else:
            await player.move_with_gui(ctx)

    @chess_group.command()
    @chess.verify_context(level="game")
    async def board(self, ctx: discord.ApplicationContext):
        """
        View the board and move history.
        """
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)

        await player.view_board(ctx)

    @chess_group.command()
    @chess.verify_context(level="player")
    async def forfeit(self, ctx: discord.ApplicationContext):
        """
        Forfeit the game.
        """
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
                "Forfeit this game?"
            )
        else:
            msg = (
                "Forfeiting will immediately end the game for both you and your opponent. This can't be undone.\n"
                "\n"
                "Forfeit this game?"
            )

        embed = discord.Embed(
            title="Are you sure?", description=msg, color=support.Color.caution()
        )

        view = support.ConfirmationView(ctx=ctx)

        confirmation = await view.request_confirmation(
            prompt_embeds=[embed], ephemeral=True
        )

        if confirmation:
            await ctx.interaction.edit_original_response(
                content="Forfeiting the game...", view=None, embeds=[]
            )
            await player.forfeit()
        else:
            await ctx.interaction.edit_original_response(
                content=f"Okay! The game is still on.", view=None, embeds=[]
            )

    @chess_group.command()
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
        """
        Make or rescind a proposal to draw.
        """
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)
        if mode == "Propose":
            if player.has_proposed_draw:
                msg = "You'll need to resicind your current proposal before you can make a new one."
                embed = discord.Embed(
                    title="You've already proposed a draw.",
                    description=msg,
                    color=support.Color.error(),
                )
                await ctx.respond(embed=embed, ephemeral=True)
            else:
                msg = (
                    f"If you think it's time to wrap things up, you can propose a draw. If "
                    f"{player.opponent.user.mention} accepts, the game will end in a draw, with neither player "
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
                    color=support.Color.caution(),
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
                    color=support.Color.error(),
                )

                await ctx.respond(embed=embed, ephemeral=True)
            else:
                await ctx.respond(content="Rescinding your proposal...", ephemeral=True)
                await player.rescind_draw()

    @chess_group.command()
    async def replay(self, ctx: discord.ApplicationContext):
        """
        Review and replay your past chess games.
        """
        view = chess.ChessReplayMenuView(ctx=ctx)
        await view.initiate_view()

    @commands.Cog.listener(name="on_thread_member_remove")
    async def sync_game_thread_removal(self, thread_member: discord.ThreadMember):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(
            thread_member.thread_id
        )
        player: chess.ChessPlayer = chess_game.retrieve_player(thread_member)

        if player:
            await player.forfeit()

            msg = (
                f"I forfeited your chess game against {player.opponent.user.mention} in {chess_game.guild} "
                f"on your behalf because you left the game thread."
            )

            embed = discord.Embed(
                title="Chess Game Forfeited",
                description=msg,
                color=support.Color.error(),
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
