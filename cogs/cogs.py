import discord
from discord.commands import Option, SlashCommandGroup, slash_command
from discord.ext import commands

import cogs.uno.functions
import support
from cogs import about, rps, uno


class CogMaster(commands.Cog):
    """
    A custom ``Cog`` class that extends Pycord's ``Cog`` class and that all of 3515.games' cogs inherit from.
    """

    def __init__(self, bot: discord.Bot):
        self.bot = bot


class AboutCog(CogMaster):
    """
    The cog for the About module, which displays meta information about 3515.games.
    """

    def __init__(self, **kwargs):
        super(AboutCog, self).__init__(**kwargs)

    @slash_command(description="View version, copyright, and legal information for 3515.games.")
    async def about(self, ctx):
        await about.AboutView(ctx=ctx).show_about()


class RockPaperScissorsCog(CogMaster):
    """
    The cog for the Rock-Paper-Scissors module, which facilitates Rock-Paper-Scissors matches between two members of
    the same Discord server.
    """

    def __init__(self, **kwargs):
        super(RockPaperScissorsCog, self).__init__(**kwargs)

    rps_group = SlashCommandGroup("rps", "Commands for playing Rock-Paper-Scissors.")

    @rps_group.command(description="Challenge someone to a game of Rock-Paper-Scissors.")
    async def challenge(
            self,
            ctx: discord.ApplicationContext,
            opponent: Option(discord.User, "Mention a player to be your opponent."),
            game_format: Option(str, name="format",
                                description="Choose whether to play a best-of-three, best-of-five, "
                                            "or best-of-nine match.",
                                choices=["Best of Three", "Best of Five", "Best of Nine"])
    ):
        """
        Challenges a user to a Rock-Paper-Scissors match between them and the command invoker.

        :param ctx: An ApplicationContext object.
        :param opponent: The user to be challenged.
        :param game_format: The format of the Rock-Paper-Scissors match; this can be either "Best of Three",
        "Best of Five", or "Best of Nine".
        """

        # the invoker cannot challenge themselves
        if ctx.user.id == opponent.id:
            await ctx.respond("You can't play with yourself!", ephemeral=True)
            return

        # maps game formats to the number of points needed for victory in each
        victory_points = {
            "Best of Three": 2,
            "Best of Five": 3,
            "Best of Nine": 5
        }

        # create the game object
        rps_game = rps.RPSGame(players=[rps.RPSPlayer(ctx.user), rps.RPSPlayer(opponent)],
                               game_format=game_format, points_to_win=victory_points[game_format])

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


class UnoCog(CogMaster):
    """
    The cog for the UNO module, which facilitates UNO games with up to 20 members of the same Discord server.
    """

    def __init__(self, **kwargs):
        super(UnoCog, self).__init__(**kwargs)

    uno_group = SlashCommandGroup("uno", "Commands for playing UNO.")
    create_group = uno_group.create_subgroup("creategame", "Commands for creating UNO games.")
    gamehost_group = uno_group.create_subgroup("gamehost", "Commands for UNO Game Hosts.")

    # game creation commands

    @create_group.command(name="public", description="Create a public UNO game.")
    async def create_public_game(self,
                                 ctx: discord.ApplicationContext,
                                 players: Option(
                                     int,
                                     "Choose the maximum number of players that can join your game (min. 2, max. 20). "
                                     "This includes you.", min_value=2, max_value=20
                                 ),
                                 points: Option(int, "(Optional) Choose the number of points required to win "
                                                     "(min. 100, max. 500). The default is 500.",
                                                min_value=100, max_value=500, default=500)):
        """
        Creates an UNO game and corresponding game thread.

        :param ctx: An ApplicationContext object.
        :param players: The maximum number of players that will be allowed to join the game. Minimum is 2,
            maximum is 20.
        :param points: The number of points that will be required to win the game. Minimum is 100, maximum is 500.
            Optional; defaults to 500.
        """

        # the bot must have certain permissions in order to create an UNO game
        if not await uno.functions.has_creation_permissions(ctx):
            return

        # UNO games can only be created in text channels
        if not isinstance(ctx.channel, discord.TextChannel):
            message = "You can only use that command in regular text channels - not threads. Go to a text channel," \
                      "then try again."
            embed = discord.Embed(title="You can't do that in a thread.", description=message,
                                  color=support.ExtendedColors.red())

            await ctx.respond(embed=embed, ephemeral=True)
            return

        # users may not host more than one game in the same server at a time
        user_is_hosting = uno.UnoGame.get_hosted_games(user=ctx.user, guild_id=ctx.guild_id)

        if user_is_hosting:
            message = "You're already hosting an UNO game in this server. Before you can create a new one, you must " \
                      "either complete, end, or transfer host powers for your current game.\n"
            embed = discord.Embed(title="You're already hosting a game.", description=message,
                                  color=support.ExtendedColors.red())
            game_thread_url = f"https://discord.com/channels/{ctx.guild_id}/{user_is_hosting.thread.id}"
            await ctx.respond(embed=embed, view=uno.GoToUnoThreadView(game_thread_url), ephemeral=True)
            return

        # tell the user important information about creating an UNO game
        warning_text = f"You're about to create a **public** UNO game. There are a few important things you need to " \
                       f"know:\n" \
                       f"\n" \
                       f"**UNO games are contained within " \
                       f"[threads](https://support.discord.com/hc/en-us/articles/4403205878423-Threads-FAQ).** " \
                       f"I'll handle the creation and management of the thread for you. If you can " \
                       f"``Manage Threads``, please refrain from editing or deleting the thread until the game is " \
                       f"over (trust me, I've got this).\n" \
                       f"\n" \
                       f"**Anyone can join.** Since you're creating a public UNO game, anyone who can both see and " \
                       f"talk in this channel will be able to join or spectate your game.\n" \
                       f"\n" \
                       f"**You're in control.** You'll be the Game Host for this UNO game. This entitles you to " \
                       f"certain special powers, like removing players from the game or the thread it's hosted in, " \
                       f"or ending the game early. However...\n" \
                       f"\n" \
                       f"**With power comes responsibility.** The UNO game won't start until you use " \
                       f"``/uno gamehost start``, and if you leave the thread at any time, the game will immediately " \
                       f"end for all players. For more, see the *Host Powers and Responsibilities* section of " \
                       f"``/help uno``.\n" \
                       f"\n" \
                       f"**I'm watching for inactivity.** Players determined to be inactive may be automatically " \
                       f"removed from the game by yours truly. __You're not exempt from this__, and if *you* get " \
                       f"removed, the game will end for everyone else, since you're the Game Host. Keep that in " \
                       f"mind.\n" \
                       f"\n" \
                       f"Before we start, let's review your game settings.\n" \
                       f"\n" \
                       f"__Game Settings__\n" \
                       f"**Players**: {players}\n" \
                       f"**Points to Win**: {points}\n" \
                       f"\n" \
                       f"If these settings aren't correct, hit the No button below and rerun " \
                       f"`/uno creategame public` with your intended settings. Once the game has started, these " \
                       f"settings can't be changed.\n" \
                       f"\n" \
                       f"Proceed with creating this UNO game?"

        warning_embed = discord.Embed(title="Please read this carefully.", description=warning_text,
                                      color=support.ExtendedColors.orange())

        # confirm game creation with user
        conf_data = await support.ConfirmationView(ctx=ctx).request_confirmation(prompt_embeds=[warning_embed],
                                                                                 ephemeral=True)

        conf_success = conf_data["success"]
        conf_prompt = conf_data["prompt"]

        if conf_success:
            # create an UnoGame object and associated game thread
            await conf_prompt.edit_original_message(content="Creating your UNO game...", embeds=[], view=None)
            game_thread = await ctx.channel.create_thread(name=f"UNO with {ctx.user.name} - check pins to play!",
                                                          type=discord.ChannelType.public_thread,
                                                          auto_archive_duration=1440)

            uno_game = uno.UnoGame(guild=ctx.guild, thread=game_thread, host=ctx.user, max_players=players,
                                   points_to_win=points)
            await uno_game.waiting_room_intro()
            await uno_game.add_player(ctx, ctx.user, is_host=True)

            thread_creation_embed = discord.Embed(title="An UNO game has been created!",
                                                  description=f"{ctx.user.mention} created an UNO game! You can "
                                                              f"join the game by typing `/join` in the game thread.",
                                                  color=support.ExtendedColors.mint())

            thread_url = f"https://discord.com/channels/{ctx.guild_id}/{game_thread.id}"

            await ctx.send(embed=thread_creation_embed, view=uno.GoToUnoThreadView(thread_url=thread_url))

        else:
            cancellation_embed = discord.Embed(title="Game creation canceled.",
                                               description="You canceled the creation of this UNO game. "
                                                           "You can create a new game with `/uno creategame`.",
                                               color=support.ExtendedColors.red())

            await conf_prompt.edit_original_message(embeds=[cancellation_embed], view=None)

    # player commands

    @uno_group.command(name="join", description="Join an UNO game.")
    @uno.functions.verify_uno_context
    async def join(self, ctx: discord.ApplicationContext):
        """
        Joins the invoker to an UNO game. Can only be used in UNO game threads.

        :param ctx: An ApplicationContext object.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)

        # users can't join games they're already in
        if any(player for player in uno_game.players.itervalues() if player.user == ctx.user):
            msg = "You can't join an UNO game you're already a player in. If you meant to leave, use `/uno leave` " \
                  "instead."
            embed = discord.Embed(title="You're already in this game.", description=msg,
                                  color=support.ExtendedColors.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # users can't join games that have already started
        elif not uno_game.is_joinable:
            msg = "You can't join a game that's already in progress."
            embed = discord.Embed(title="This game has already started.", description=msg,
                                  color=support.ExtendedColors.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # users can't join games that are already full
        elif not len(uno_game.players) <= uno_game.max_players:
            msg = "You won't be able to join unless someone leaves or is removed by the Game Host."
            embed = discord.Embed(title="This game is full.", description=msg, color=support.ExtendedColors.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, the user is added to the game
        else:
            await uno_game.add_player(ctx, ctx.user)

    @uno_group.command(name="leave", description="Leave an UNO game.")
    @uno.functions.verify_uno_player
    async def leave(self, ctx: discord.ApplicationContext):
        """
        Voluntarily removes the player from an UNO game. Can only be used in UNO game threads.

        :param ctx: An ApplicationContext object.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player_node = next((player for player in uno_game.players.iternodes()
                            if player.value.user == ctx.user), None)

        if uno_game and player_node:
            leave_confirmation_msg = "If the game has already started, you won't be able to rejoin. If you're the " \
                                     "Game Host, leaving the game will end it for everyone else - consider " \
                                     "transferring your host powers to another player with `/uno gamehost transfer` " \
                                     "beforehand."

            leave_confirmation_embed = discord.Embed(title="Leave this UNO game?", description=leave_confirmation_msg,
                                                     color=support.ExtendedColors.orange())

            conf_data = await support.ConfirmationView(ctx).request_confirmation(
                prompt_embeds=[leave_confirmation_embed], ephemeral=True)

            conf_success = conf_data["success"]
            conf_prompt = conf_data["prompt"]

            if conf_success:
                await conf_prompt.edit_original_message(content="Removing you from the game...", view=None,
                                                        embeds=[])
                await uno_game.remove_player(player_node=player_node)
            else:
                await conf_prompt.edit_original_message(content="Okay! You're still in the game!", view=None,
                                                        embeds=[])

    @uno_group.command(name="hand", description="See the UNO cards you're currently holding.")
    @uno.functions.verify_active_game
    async def show_hand(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = await uno_game.retrieve_player(ctx.user)

        await player.show_hand(ctx)

    @uno_group.command(name="play", description="Play one of your UNO cards.")
    @uno.functions.verify_player_turn
    async def play_card(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = await uno_game.retrieve_player(ctx.user)

        await player.play_card(ctx)

    @uno_group.command(name="draw", description="Draw an UNO card.")
    @uno.functions.verify_player_turn
    async def draw_card(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = await uno_game.retrieve_player(ctx.user)

        await player.draw_card(ctx)

    @uno_group.command(name="newround")
    @uno.functions.verify_active_game
    async def new_round(self, ctx):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        await uno_game.start_new_round()

    # game host commands

    @gamehost_group.command(name="start", description="Start an UNO game. Game Hosts only.")
    @uno.functions.verify_uno_gamehost
    async def gamehost_start(self, ctx: discord.ApplicationContext):
        """
        Starts an UNO game that has already been created and which at least one player aside from the Game Host has
        joined. Can only be used by UNO Game Hosts in UNO game threads. Not to be confused with
        ``create_public_game()`` and ``create_private_game()``, which create UNO games that must later be started with
        this command.

        :param ctx: An ApplicationContext object.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)

        # the host can't start a game that's already in progress
        if not uno_game.is_joinable:
            embed = discord.Embed(title="This game has already started.",
                                  description="You can't start a game that's already in progress, silly!",
                                  color=support.ExtendedColors.red())

            await ctx.respond(embed=embed, ephemeral=True)

        # the host can't start a game that fewer than two players have joined
        elif len(uno_game.players) < 2:
            embed = discord.Embed(title="You need more players.",
                                  description="You can't start this game until at least two players, including "
                                              "yourself, have joined.",
                                  color=support.ExtendedColors.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, the host is asked to confirm that they want to start the game
        else:
            conf_embed = discord.Embed(title="Start this UNO game?",
                                       description="Once the game has begun, no new players will be able to join.",
                                       color=support.ExtendedColors.orange())

            conf_data = await support.ConfirmationView(ctx=ctx).request_confirmation(prompt_embeds=[conf_embed],
                                                                                     ephemeral=True)

            conf_success, conf_prompt = conf_data["success"], conf_data["prompt"]

            if conf_success:
                await conf_prompt.edit_original_message(content="Let's get started!", embeds=[], view=None)
                await uno_game.host_start_game()

            else:
                await conf_prompt.edit_original_message(content="Okay! Just use `/uno gamehost start` "
                                                                "whenever you're ready.",
                                                        embeds=[],
                                                        view=None)

    @gamehost_group.command(name="abort", description="Abort an UNO game. Game Hosts only.")
    @uno.functions.verify_uno_gamehost
    async def gamehost_abort(self, ctx: discord.ApplicationContext):
        """
        Aborts an ongoing UNO game, forcefully ending it for all players. Can only be used by UNO Game Hosts in UNO game
        threads.

        :param ctx: An ApplicationContext object.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        message = "Proceeding will immediately end the game and lock the thread for all players, including you.\n" \
                  "\n" \
                  "This can't be undone."
        embed = discord.Embed(title="Abort this UNO game?", description=message, color=support.ExtendedColors.orange())
        conf_data = await support.ConfirmationView(ctx=ctx).request_confirmation(prompt_embeds=[embed],
                                                                                 ephemeral=True)
        conf_success = conf_data["success"]
        conf_prompt = conf_data["prompt"]

        if conf_success:
            await conf_prompt.edit_original_message(content="Aborting your UNO game...", embeds=[], view=None)
            await uno_game.host_abort_game()
        else:
            await conf_prompt.edit_original_message(content="Okay! Abortion canceled.", embeds=[], view=None)

    @commands.Cog.listener()
    async def on_thread_member_remove(self, thread_member: discord.ThreadMember):
        """
        A listener that runs whenever a user is removed from a thread. This runs whenever *any* user is removed from
        *any* thread in the server, whether or not they are playing an UNO game or being removed from an UNO game
        thread. The purpose of this listener is to enable the automatic removal of UNO players from games when they
        leave associated game threads.

        :param thread_member: A discord.ThreadMember object representing the removed user.
        """
        uno_game = uno.UnoGame.retrieve_game(thread_member.thread_id)
        player_node = next((player for player in uno_game.players.iternodes()
                            if player.value.user.id == thread_member.id), None)

        # only call remove_player() if the thread is an UNO game thread AND the user is a player in that game
        if uno_game and player_node:
            await uno_game.remove_player(player_node=player_node)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        """
        A listener that runs whenever a thread is deleted. This runs whenever *any* thread in the server is deleted,
        whether or not is an UNO game thread. The purpose of this listener is to enable the automatic closure of UNO
        games whose associated game threads are deleted.

        :param thread: The deleted thread.
        """
        uno_game = uno.UnoGame.retrieve_game(thread.id)

        # only call force_close_thread_deletion() if the deleted thread is associated with an UNO game
        if uno_game:
            await uno.UnoGame.force_close_thread_deletion(uno_game)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """
        A listener that runs whenever a channel is deleted. This runs whenever *any* channel in the server is deleted,
        whether or not it contains UNO game threads. The purpose of this listener is to enable the automatic closure
        of UNO games whose associated game threads' parent channels are deleted.

        :param channel: The deleted channel.
        """
        # call force_close_channel_deletion() for all channel threads associated with UNO games
        for thread in [thread for thread in channel.threads if thread.id in uno.UnoGame.__all_games__.keys()]:
            uno_game = uno.UnoGame.retrieve_game(thread.id)
            await uno.UnoGame.force_close_channel_deletion(uno_game)
