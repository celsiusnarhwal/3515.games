import discord
from discord.commands import Option, SlashCommandGroup, slash_command
from discord.ext import commands
from llist import dllistnode

import support
from cogs import about, rps, uno, chess


class MasterCog(commands.Cog):
    """
    A subclass of :class:`commands.Cog` that all of 3515.games' cogs inherit from.
    """

    # pycord requires that all cogs use this exact constructor, so we save a little bit of typing by having them all
    # inherit from MasterCog. yay!
    def __init__(self, bot: discord.Bot):
        self.bot = bot


class AboutCog(MasterCog):
    """
    The cog for the About module, which displays meta information about 3515.games.
    """

    @slash_command(description="Allow me to reintroduce myself.")
    async def about(self, ctx):
        await about.AboutView(ctx=ctx).show_about()


class RockPaperScissorsCog(MasterCog):
    """
    The cog for the Rock-Paper-Scissors module, which facilitates Rock-Paper-Scissors matches between two members of
    the same Discord server.
    """
    rps_group = SlashCommandGroup("rps", "Commands for playing Rock-Paper-Scissors.")

    @rps_group.command(description="Challenge someone to a game of Rock-Paper-Scissors.")
    @support.helpers.bot_has_permissions(support.GamePermissions.rps())
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

        # the user cannot challenge themselves
        if ctx.user == opponent:
            msg = "You can't play with yourself. Choose someone else to challenge."
            embed = discord.Embed(title="Make some friends, please.", description=msg, color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # the user cannot challenge the bot
        elif opponent == ctx.me:
            msg = "Unfortunately, my creator is too merciful to allow me to utterly decimate you at " \
                  "Rock-Paper-Scissors.\n" \
                  "\n" \
                  "Challenge someone else."
            embed = discord.Embed(title="Not happening.", description=msg, color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # the user cannot challenge other bots
        elif opponent.bot:
            msg = "You can only play with real people. Choose someone else to challenge."
            embed = discord.Embed(title="That's a bot.", description=msg, color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        else:
            # map game formats to the number of points needed for victory in each
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


class UnoCog(MasterCog):
    """
    The cog for the UNO module, which facilitates UNO games with up to 20 members of the same Discord server.
    """
    uno_group = SlashCommandGroup("uno", "Commands for playing UNO.")
    create_group = uno_group.create_subgroup("create", "Commands for creating UNO games.")
    gamehost_group = uno_group.create_subgroup("host", "Commands for UNO Game Hosts.")

    # game creation commands

    @create_group.command(name="public", description="Create a public UNO game.")
    @support.helpers.bot_has_permissions(support.GamePermissions.uno_public())
    @support.helpers.invoked_in_text_channel()
    @uno.helpers.verify_host_uniqueness()
    async def create_public_game(self,
                                 ctx: discord.ApplicationContext,
                                 players: Option(
                                     int,
                                     "Choose how many players can join your game (min. 2, max. 20). "
                                     "This includes you. The default is 20.", min_value=2, max_value=20, default=20
                                 ),
                                 points: Option(int, "Choose the number of points required to win "
                                                     "(max. 1000). The default is 500.",
                                                min_value=0, max_value=1000, default=500),
                                 timeout: Option(int, "Choose how many seconds players must finish their turns in "
                                                      "(min. 30, max. 120). The default is 60.",
                                                 min_value=30, max_value=120, default=60)):
        """
        Creates an UNO game and corresponding game thread.

        :param ctx: An ApplicationContext object.
        :param players: The maximum number of players that will be allowed to join the game. Minimum is 2,
            maximum is 20.
        :param points: The number of points that will be required to win the game. Minimum is 100, maximum is 500.
            Optional; defaults to 500.
        :param timeout: The number of seconds each player will have to move when its their turn.
        """

        # tell the user important information about creating an UNO game
        msg = f"You're about to create a **public** UNO game. There are a few important things you need to " \
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
              f"**With power comes responsibility.** The game won't start until you use " \
              f"``/uno host start``, and if you leave the game or its thread at any time, the game will immediately " \
              f"end for all players. For more, see the *Host Powers and Responsibilities* section of " \
              f"``/help UNO``.\n" \
              f"\n" \
              f"**I'm watching for inactivity.** Players determined to be inactive may be automatically " \
              f"removed from the game by yours truly. __You're not exempt from this__, and if *you* get " \
              f"removed, the game will end for everyone else, since you're the Game Host. Keep that in " \
              f"mind.\n" \
              f"\n" \
              f"Before we start, let's review your game settings.\n" \
              f"\n" \
              f"__Game Settings__\n" \
              f"**Maximum Players**: {players}\n" \
              f"**Points to Win**: {points}\n" \
              f"**Timeout**: {timeout} seconds\n" \
              f"\n" \
              f"If these settings aren't correct, hit the No button below and rerun " \
              f"`/uno create public` with your intended settings. Once the game has been created, these " \
              f"settings can't be changed.\n" \
              f"\n" \
              f"Proceed with creating this UNO game?"

        embed = discord.Embed(title="Creating a Public UNO Game", description=msg,
                              color=support.Color.orange())

        # confirm game creation with user
        view = support.ConfirmationView(ctx=ctx)
        confirmation = await view.request_confirmation(prompt_embeds=[embed], ephemeral=True)

        if confirmation:
            # create an UnoGame object and associated game thread
            await ctx.interaction.edit_original_message(content="Creating your UNO game...", embeds=[], view=None)
            game_thread = await ctx.channel.create_thread(name=f"UNO with {ctx.user.name} - check pins to play!",
                                                          type=discord.ChannelType.public_thread,
                                                          auto_archive_duration=1440)

            game_settings = uno.UnoGameSettings(max_players=players, points_to_win=points, timeout=timeout)
            uno_game = uno.UnoGame(guild=ctx.guild, thread=game_thread, host=ctx.user, settings=game_settings)
            await uno_game.open_lobby()
            await uno_game.add_player(ctx, ctx.user, is_host=True)

            embed = discord.Embed(title="An UNO game has been created!",
                                  description=f"{ctx.user.mention} created an UNO game! You can "
                                              f"join the game by typing `/uno join` in the "
                                              f"game thread.",
                                  color=support.Color.mint())

            thread_url = f"https://discord.com/channels/{game_thread.guild.id}/{game_thread.id}"

            await ctx.send(embed=embed, view=support.GoToGameThreadView(thread_url=thread_url))

            await uno_game.game_timer()

        else:
            cancellation_embed = discord.Embed(title="Game Creation Canceled",
                                               description="You canceled the creation of this UNO game. "
                                                           f"You can create a new game with "
                                                           f"`/{ctx.command.qualified_name}`.",
                                               color=support.Color.red())

            await ctx.interaction.edit_original_message(embeds=[cancellation_embed], view=None)

    # TODO implement private games
    @create_group.command(name="private",
                          description="Create a private UNO game. Requires Server Boost Level 2 or higher.")
    @support.helpers.bot_has_permissions(support.GamePermissions.uno_private())
    @support.helpers.invoked_in_text_channel()
    @uno.helpers.verify_host_uniqueness()
    async def create_private_game(self, ctx: discord.ApplicationContext):
        if ctx.guild.premium_tier < 2:
            msg = "Discord won't let me create private UNO games in this server until it's reached Boost Level 2 " \
                  "or higher."
            embed = discord.Embed(title="Boost your server first.", description=msg, color=support.Color.red())

            await ctx.respond(embed=embed, view=support.ServerBoostURLView(), ephemeral=True)

    # player commands

    @uno_group.command(name="join", description="Join an UNO game.")
    @uno.helpers.verify_context(level="thread")
    async def join(self, ctx: discord.ApplicationContext):
        """
        Joins the invoker to an UNO game. Can only be used in UNO game threads.

        :param ctx: An ApplicationContext object.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)

        # users can't join games they're already in
        if uno_game.retrieve_player(ctx.user):
            msg = "You can't join an UNO game you're already a player in. If you meant to leave, use `/uno leave` " \
                  "instead."
            embed = discord.Embed(title="You're already in this game.", description=msg,
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # users can't join games they're banned from
        elif ctx.user in uno_game.banned_users:
            msg = "You're banned from this game, so you can't play in it."
            embed = discord.Embed(title="You're banned from this game.", description=msg,
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # users can't join games that have already started
        elif not uno_game.is_joinable:
            msg = "You can't join a game that's already in progress."
            embed = discord.Embed(title="This game has already started.", description=msg,
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # users can't join games that are already full
        elif not len(uno_game.players) <= uno_game.settings.max_players:
            msg = "You won't be able to join unless someone leaves or is removed by the Game Host."
            embed = discord.Embed(title="This game is full.", description=msg, color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, the user is added to the game
        else:
            await uno_game.add_player(ctx, ctx.user)

    @uno_group.command(name="leave", description="Leave an UNO game.")
    @uno.helpers.verify_context(level="player")
    async def leave(self, ctx: discord.ApplicationContext):
        """
        Voluntarily removes the player from an UNO game. Can only be used in UNO game threads.

        :param ctx: An ApplicationContext object.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player_node = uno_game.retrieve_player(ctx.user, return_node=True)

        if uno_game and player_node:
            msg = "If the game has already started, you won't be able to rejoin. If you're the " \
                  "Game Host, leaving the game will end it for everyone else - consider " \
                  "transferring your host powers to another player with `/uno host transfer` " \
                  "beforehand."

            embed = discord.Embed(title="Leave this UNO game?", description=msg,
                                  color=support.Color.orange())

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(
                prompt_embeds=[embed], ephemeral=True)

            if confirmation:
                await ctx.interaction.edit_original_message(content="Removing you from the game...", view=None,
                                                            embeds=[])
                await uno_game.remove_player(player_node=player_node)
            else:
                await ctx.interaction.edit_original_message(content="Okay! You're still in the game!", view=None,
                                                            embeds=[])

    @uno_group.command(name="hand", description="See the UNO cards you're currently holding.")
    @uno.helpers.verify_context(level="game")
    async def show_hand(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = uno_game.retrieve_player(ctx.user)

        await player.show_hand(ctx)

    @uno_group.command(name="play", description="Play one of your UNO cards.")
    @uno.helpers.verify_context(level="turn")
    async def play_card(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = uno_game.retrieve_player(ctx.user)

        await player.select_card(ctx)

    @uno_group.command(name="draw", description="Draw an UNO card.")
    @uno.helpers.verify_context(level="turn")
    async def draw_card(self, ctx: discord.ApplicationContext):

        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = uno_game.retrieve_player(ctx.user)

        await player.draw_card(ctx)

    @uno_group.command(name="uno", description="Say 'UNO!' when you have one card left.")
    @uno.helpers.verify_context(level="game")
    async def say_uno(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player = uno_game.retrieve_player(ctx.user)

        if not len(player.hand) == 1:
            msg = "You can only say 'UNO!' when you have one card left."
            embed = discord.Embed(title="Get rid of those cards first.", description=msg,
                                  color=support.Color.red())

            await ctx.respond(embed=embed, ephemeral=True)
        elif player.has_said_uno:
            msg = "You've already said UNO. Unless you draw more cards before getting rid of your last one, " \
                  "you won't be able to say it again."
            embed = discord.Embed(title="You did that already.", description=msg,
                                  color=support.Color.red())

            await ctx.respond(embed=embed, ephemeral=True)
        else:
            msg = "Saying 'UNO!' will notify all other players that you have only one card left. Aside from that, " \
                  "saying 'UNO!' does nothing else.\n" \
                  "\n" \
                  "Say UNO?"
            embed = discord.Embed(title="Say UNO?", description=msg, color=support.Color.orange())

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(prompt_embeds=[embed], ephemeral=True)

            if confirmation:
                await ctx.interaction.edit_original_message(content="Roger that! <:ritsu_salute:727962077888512221>",
                                                            embeds=[],
                                                            view=None)
                await player.say_uno()
            else:
                await ctx.interaction.edit_original_message(content="Better hope you don't get called out, then. 😒",
                                                            embeds=[], view=None)

    @uno_group.command(name="callout", description="Call out a player for failing to say 'UNO!'.")
    @uno.helpers.verify_context(level="turn")
    async def callout(self,
                      ctx: discord.ApplicationContext,
                      receiving_player: Option(discord.User, "Mention a player to call out.", name="player")):

        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player: uno.UnoPlayer = uno_game.retrieve_player(ctx.user)
        recipient: uno.UnoPlayer = uno_game.retrieve_player(receiving_player)

        if not recipient:
            embed = discord.Embed(title="That's not a player.",
                                  description="You can only call out users who are also players in this UNO game.",
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)
        elif player == recipient:
            embed = discord.Embed(title="Come on, man.",
                                  description="This should really go without saying, but you can't call out "
                                              "yourself. Choose another player to call out.",
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            await player.callout(ctx=ctx, recipient=recipient)

    @uno_group.command(name="status", description="Open the UNO Status Center.")
    @uno.helpers.verify_context(level="thread")
    async def status(self, ctx: discord.ApplicationContext):
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)

        view = uno.UnoStatusCenterView(ctx=ctx, game=uno_game)
        await view.open_status_center()

    # game host commands
    @gamehost_group.command(name="start", description="Start an UNO game. Game Hosts only.")
    @uno.helpers.verify_context(level="thread", verify_host=True)
    async def start_game(self, ctx: discord.ApplicationContext):
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
                                  color=support.Color.red())

            await ctx.respond(embed=embed, ephemeral=True)

        # the host can't start a game that fewer than two players have joined
        elif len(uno_game.players) < 2:
            embed = discord.Embed(title="You need more players.",
                                  description="You can't start this game until at least two players, including "
                                              "yourself, have joined.",
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, the host is asked to confirm that they want to start the game
        else:
            embed = discord.Embed(title="Start this UNO game?",
                                  description="Once the game has begun, no new players will be able to join.",
                                  color=support.Color.orange())

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(prompt_embeds=[embed], ephemeral=True)

            if confirmation:
                await ctx.interaction.edit_original_message(content="Let's get started!", embeds=[], view=None)
                await uno_game.start_game()

            else:
                await ctx.interaction.edit_original_message(content="Okay! Just use `/uno host start` "
                                                                    "whenever you're ready.",
                                                            embeds=[],
                                                            view=None)

    @gamehost_group.command(name="abort", description="Abort an UNO game. Game Hosts only.")
    @uno.helpers.verify_context(level="thread", verify_host=True)
    async def abort_game(self, ctx: discord.ApplicationContext):
        """
        Aborts an ongoing UNO game, forcefully ending it for all players. Can only be used by UNO Game Hosts in UNO game
        threads.

        :param ctx: An ApplicationContext object.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        message = "Proceeding will immediately end the game and lock the thread for all players, including you.\n" \
                  "\n" \
                  "This can't be undone."
        embed = discord.Embed(title="Abort this UNO game?", description=message, color=support.Color.orange())

        view = support.ConfirmationView(ctx=ctx)
        confirmation = await view.request_confirmation(prompt_embeds=[embed], ephemeral=True)

        if confirmation:
            await ctx.interaction.edit_original_message(content="Aborting your UNO game...", embeds=[], view=None)
            await uno_game.abort_game()
        else:
            await ctx.interaction.edit_original_message(content="Okay! The game is still on.", embeds=[], view=None)

    @gamehost_group.command(name="kick", description="Kick a player from an UNO game. Game Hosts only.")
    @uno.helpers.verify_context(level="thread", verify_host=True)
    async def kick_player(self, ctx: discord.ApplicationContext,
                          player: Option(discord.User, "Mention a player to kick.")):
        """
        Kicks a player from an UNO game. Can only be used by UNO Game Hosts in UNO game threads.

        :param player: The player to kick.
        :param ctx: An ApplicationContext object.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)
        player_node: dllistnode = uno_game.retrieve_player(player, return_node=True)

        if not player_node:
            embed = discord.Embed(title="That's not a player.",
                                  description="You can't kick someone who isn't a player in this game.",
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)
        elif player == ctx.user:
            embed = discord.Embed(title="Um, that's you.",
                                  description="You can't kick yourself. If you want out, use `/uno leave` "
                                              "(consider transferring your host powers to someone else first, "
                                              "though).",
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            msg = f"{player.mention} will be able to rejoin the game if it hasn't already started. " \
                  f"If they don't rejoin, they'll remain a spectator.\n" \
                  f"\n" \
                  f"If you want to permanently remove them from both the game and the thread, " \
                  f"use `/uno host ban` instead.\n" \
                  f"\n" \
                  f"Kick {player.mention}?"

            embed = discord.Embed(title=f"Kick {player.name}?", description=msg,
                                  color=support.Color.orange())

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(prompt_embeds=[embed], ephemeral=True)

            if confirmation:
                await ctx.interaction.edit_original_message(content=f"Kicking {player.name}...",
                                                            embeds=[],
                                                            view=None)
                await uno_game.kick_player(player_node)
            else:
                await ctx.interaction.edit_original_message(content=f"Okay! {player.mention} remains in the game.",
                                                            embeds=[], view=None)

    @gamehost_group.command(name="ban", description="Ban a user from an UNO game thread. Game Hosts only.")
    @uno.helpers.verify_context(level="thread", verify_host=True)
    async def ban_player(self, ctx: discord.ApplicationContext,
                         user: Option(discord.User, "Mention a user to ban.")):
        """
        Bans a user from an UNO game thread. Can only be used by UNO Game Hosts in UNO game threads.

        :param user: The player to ban.
        :param ctx: An ApplicationContext object.
        """
        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)

        # the host can't ban the bot
        if user == ctx.me:
            embed = discord.Embed(title="Haha, no.",
                                  description="You can't ban me. Choose someone else.",
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # the host can't ban players who're already banned
        elif user in uno_game.banned_users:
            embed = discord.Embed(title="That user is already banned.",
                                  description="You can't ban someone who's already banned.",
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # the host can't ban players who aren't in the thread
        elif not discord.utils.find(lambda x: x.id == user.id, await uno_game.thread.fetch_members()):
            embed = discord.Embed(title="That user isn't in the thread.",
                                  description="You can't ban someone who isn't in the game thread.",
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # the host can't ban themselves
        elif user == ctx.user:
            embed = discord.Embed(title="Um, that's you.",
                                  description="You can't ban yourself. If you want out, use `/uno leave` "
                                              "(consider transferring your host powers to someone else first, "
                                              "though).",
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # the host can't ban server moderators
        elif ((discord.Permissions.manage_threads.flag | discord.Permissions.administrator.flag) &
              ctx.channel.permissions_for(user).value):
            embed = discord.Embed(title="You can't ban moderators.",
                                  description="Users with the `Manage Threads` permission are immune to being banned "
                                              "(you can still `/uno host kick` them if they're a player, though).",
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, confirm the ban with the host
        else:
            msg = f"{user.mention} will be permanently removed from the game thread. If they're a player in this " \
                  f"game, they'll be permanently removed from the game, too.\n" \
                  f"\n" \
                  f"If you *only* want to remove them from the game, use `/uno host kick` instead.\n" \
                  f"\n" \
                  f"This action cannot be undone.\n" \
                  f"\n" \
                  f"Ban {user.mention}?"

            embed = discord.Embed(title=f"Ban {user.name}?", description=msg,
                                  color=support.Color.orange())

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(prompt_embeds=[embed], ephemeral=True)

            if confirmation:
                await ctx.interaction.edit_original_message(content=f"Banning {user.name}...",
                                                            embeds=[], view=None)

                player_node: dllistnode = uno_game.retrieve_player(user, return_node=True)

                if player_node:
                    await uno_game.ban_player(player_node)
                else:
                    await uno_game.ban_spectator(user)
            else:
                await ctx.interaction.edit_original_message(content=f"Okay! {user.mention} remains in the game.",
                                                            embeds=[], view=None)

    @gamehost_group.command(name="transfer",
                            description="Transfer your host powers to another player. Game Hosts only.")
    @uno.helpers.verify_context(level="thread", verify_host=True)
    async def transfer_host(self,
                            ctx: discord.ApplicationContext,
                            player: Option(discord.User, "Mention the player you want to transfer host "
                                                         "powers to.")):

        uno_game = uno.UnoGame.retrieve_game(ctx.channel_id)

        # user cannot transfer host powers to themselves
        if player.id == ctx.user.id:
            msg = "Choose another player to transfer host powers to."
            embed = discord.Embed(title="You can't transfer host powers to yourself.", description=msg,
                                  color=support.Color.red())

            await ctx.respond(embed=embed, ephemeral=True)

        # user cannot transfer host powers to non-players
        elif not uno_game.retrieve_player(player):
            msg = "The new Game Host must be a player in this UNO game."
            embed = discord.Embed(title="That person's not a player.", description=msg,
                                  color=support.Color.red())

            await ctx.respond(embed=embed, ephemeral=True)

        # user cannot transfer host powers to players already hosting another game in the same server
        elif uno.UnoGame.find_hosted_games(player, ctx.guild_id):
            msg = "You can't transfer host powers to someone who's already hosting an UNO game in this server."
            embed = discord.Embed(title="That player's already hosting a game.", description=msg,
                                  color=support.Color.red())

            await ctx.respond(embed=embed, ephemeral=True)

        # if none of the above conditions are met, the user is asked to confirm the transfer
        else:
            msg = f"{player.mention} will become the Game Host, effective immediately, and all associated powers " \
                  f"will become exclusively theirs to use. Conversely, you will lose your status as Game Host " \
                  f"and will no longer be able to use any of the powers that come with the title.\n" \
                  f"\n" \
                  f"You will remain a player in this UNO game until it ends or you choose to leave.\n" \
                  f"\n" \
                  f"This action cannot be undone.\n" \
                  f"\n" \
                  f"Do you want to make {player.name} the Game Host?"

            embed = discord.Embed(title=f"Make {player.name} the Game Host?", description=msg,
                                  color=support.Color.orange())

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(prompt_embeds=[embed], ephemeral=True)

            if confirmation:
                await ctx.interaction.edit_original_message(content=f"Transferring host powers to {player.mention}...",
                                                            embeds=[], view=None)
                await uno_game.transfer_host(player)

            else:
                await ctx.interaction.edit_original_message(content="Ok! You're still the Game Host.",
                                                            embeds=[],
                                                            view=None)

    @commands.Cog.listener()
    async def on_thread_member_join(self, thread_member: discord.ThreadMember):
        """
        A listener that runs whenever a user joins a thread. This runs whenever *any* user joins *any* thread in the
        server, regardless of whether it's an UNO game thread. The purpose of this listener is to enable the bot to
        automatically remove the user from the thread if they have been banned from the associated UNO game.

        This listener is only effective on public threads; with private threads, Discord provides functionality
        to properly bar users from rejoining threads they've been removed from.

        :param thread_member: The user who joined the thread.
        """

        uno_game = uno.UnoGame.retrieve_game(thread_member.thread_id)

        if uno_game:
            if discord.utils.find(lambda user: user.id == thread_member.id, uno_game.banned_users):
                await thread_member.thread.remove_user(thread_member)
                await thread_member.thread.purge(limit=2, check=lambda message: message.author.id == thread_member.id)

    @commands.Cog.listener()
    async def on_thread_member_remove(self, thread_member: discord.ThreadMember):

        """
        A listener that runs whenever a user is removed from a thread. This runs whenever *any* user is removed from
        *any* thread in the server, regardless of whether they're playing an UNO game or being removed from an UNO game
        thread. The purpose of this listener is to enable the automatic removal of UNO players from games when they
        leave associated game threads.

        :param thread_member: A discord.ThreadMember object representing the removed user.
        """
        uno_game = uno.UnoGame.retrieve_game(thread_member.thread_id)
        player_node = uno_game.retrieve_player(thread_member, return_node=True)

        # only call remove_player() if the thread is an UNO game thread AND the user is a player in that game
        if player_node:
            await uno_game.remove_player(player_node=player_node)

    @commands.Cog.listener()
    async def on_raw_thread_delete(self, thread: discord.RawThreadDeleteEvent):
        """
        A listener that runs whenever a thread is deleted. This runs whenever *any* thread in the server is deleted,
        whether or not is an UNO game thread. The purpose of this listener is to enable the automatic closure of UNO
        games whose associated game threads are deleted.

        :param thread: A discord.RawThreadDeleteEvent object representing the deleted thread.
        """
        uno_game = uno.UnoGame.retrieve_game(thread.thread_id)

        # only call force_close_thread_deletion() if the deleted thread is associated with an UNO game
        if uno_game:
            await uno_game.force_close(reason="thread_deletion")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """
        A listener that runs whenever a channel is deleted. This runs whenever *any* channel in the server is deleted,
        whether or not it contains UNO game threads. The purpose of this listener is to enable the automatic closure
        of UNO games whose associated game threads' parent channels are deleted.

        :param channel: The deleted channel.
        """
        # call force_close_channel_deletion() for all channel threads associated with UNO games
        for thread in [thread for thread in channel.threads if thread.id in uno.UnoGame.retrieve_game(thread.id)]:
            uno_game = uno.UnoGame.retrieve_game(thread.id)
            await uno_game.force_close(reason="channel_deletion")


class ChessCog(MasterCog):
    """
    The cog for the chess modules, which facilitates chess games between two members of the same Discord server.
    """
    chess_group = SlashCommandGroup("chess", "Commands for playing chess.")

    @chess_group.command(description="Challenge someone to a game of chess.")
    @support.helpers.bot_has_permissions(support.GamePermissions.chess())
    @support.helpers.invoked_in_text_channel()
    async def challenge(self,
                        ctx: discord.ApplicationContext,
                        opponent: Option(discord.User, "Mention a user to be your opponent."),
                        saving: Option(str, "Choose whether to enable game saving. Defaults to Enabled.",
                                       choices=["Enabled", "Disabled"], default="Enabled")):

        saving = True if saving == "Enabled" else False

        if ctx.user == opponent:
            msg = "You can't play with yourself. Choose someone else to challenge."
            embed = discord.Embed(title="Make some friends, please.", description=msg, color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        elif opponent == ctx.me:
            msg = "Even if my creator allowed me to play with you, I would checkmate you in short order, " \
                  "because I am better than you at everything.\n" \
                  "\n" \
                  "Challenge someone else."
            embed = discord.Embed(title="No.", description=msg, color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        elif opponent.bot:
            msg = "You can only play with real people. Choose someone else to challenge."
            embed = discord.Embed(title="That's a bot.", description=msg, color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        elif chess.ChessGame.retrieve_duplicate_game(players=[ctx.user, opponent], guild=ctx.guild):
            chess_game = chess.ChessGame.retrieve_duplicate_game(players=[ctx.user, opponent], guild=ctx.guild)
            msg = f"You're in an ongoing chess match with {opponent.mention} in this server. " \
                  f"You'll need to wrap it up before you can challenge them to another one."
            embed = discord.Embed(title=f"You're already playing with {opponent.name}.", description=msg,
                                  color=support.Color.red())
            thread_url = f"https://discord.com/channels/{chess_game.guild.id}/{chess_game.thread.id}"
            await ctx.respond(embed=embed, view=support.GoToGameThreadView(thread_url=thread_url), ephemeral=True)

        else:
            # confirm with the challenger (i.e. the invoker of /chess challenge) that they want to issue the challenge

            msg = f"You're about to challenge {opponent.mention} to a game of chess. There are a few important " \
                  f"things you need to know:\n" \
                  f"\n" \
                  f"**Chess games are contained within [threads]" \
                  f"(https://support.discord.com/hc/en-us/articles/4403205878423-Threads-FAQ).** I'll handle the " \
                  f"creation and management of the thread for you. If you can `Manage Threads`, please refrain from " \
                  f"editing or deleting the thread until the game is over (trust me, I've got this).\n" \
                  f"\n" \
                  f"**Anyone can spectate.** Anyone who can both see and talk in this channel can spectate your " \
                  f"game. However, only you and your opponent will be able to talk in the game thread.\n" \
                  f"\n" \
                  f"**I'm watching for inactivity.** If I determine either you or your opponent to have gone AFK, " \
                  f"I can forfeit the game on your behalves. Watch out.\n" \
                  f"\n" \
                  f"Challenge {opponent.mention} to a game of chess?"

            embed = discord.Embed(title="Creating a Chess Game", description=msg, color=support.Color.orange())

            view = support.ConfirmationView(ctx=ctx)
            challenge_confirmation = await view.request_confirmation(
                prompt_embeds=[embed],
                ephemeral=True
            )

            if challenge_confirmation:
                # ask the challenge recipient whether they accept the challenge
                await ctx.interaction.edit_original_message(content=f"Waiting on {opponent.mention}...",
                                                            embeds=[],
                                                            view=None)

                view = support.GameChallengeResponseView(ctx=ctx,
                                                         target_user=opponent,
                                                         challenger=ctx.user,
                                                         game_name="chess"
                                                         )

                challenge_acceptance = await view.request_response()

                if not challenge_acceptance:
                    return
            else:
                if challenge_confirmation is not None:
                    await ctx.interaction.edit_original_message(content="Okay! Your challenge was canceled.",
                                                                embeds=[],
                                                                view=None)
                    return

            # create a new chess game
            game_thread = await ctx.channel.create_thread(
                name=f"Chess - {ctx.user.name} vs. {opponent.name}",
                type=discord.ChannelType.public_thread,
                auto_archive_duration=1440
            )

            chess_game = chess.ChessGame(thread=game_thread, players=[ctx.user, opponent], saving_enabled=saving)

            await chess_game.open_lobby()

            await game_thread.add_user(ctx.user)
            await game_thread.add_user(opponent)

            embed = discord.Embed(title="A chess game has begun!",
                                  description=f"{ctx.user.mention} has challenged {opponent.mention} "
                                              f"to a game of chess. You can spectate their match by going to the "
                                              f"game thread.",
                                  color=support.Color.mint())

            thread_url = f"https://discordapp.com/channels/{game_thread.guild.id}/{game_thread.id}"

            await ctx.send(embed=embed, view=support.GoToGameThreadView(thread_url=thread_url))

            await chess_game.game_timer()

    @chess_group.command(description="Identify yourself as ready to begin a chess match.")
    @chess.helpers.verify_context(level="player")
    async def ready(self, ctx: discord.ApplicationContext):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)

        if player.is_ready:
            msg = "You've already readied yourself with `/chess ready`."
            embed = discord.Embed(title="You're already ready.", description=msg, color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            msg = "The match will begin as soon as both players are ready. Make sure you really are ready to play; " \
                  "once you select the Yes button below, you won't be able to change your mind.\n" \
                  "\n" \
                  "Identify yourself as ready?"
            embed = discord.Embed(title="Ready to play?", description=msg, color=support.Color.orange())

            view = support.ConfirmationView(ctx=ctx)
            confirmation = await view.request_confirmation(prompt_embeds=[embed], ephemeral=True)

            if confirmation:
                await ctx.interaction.edit_original_message(content=f"You're ready to go. Waiting on "
                                                                    f"{player.opponent.user.mention}...",
                                                            view=None,
                                                            embeds=[])
                await player.ready()
            else:
                await ctx.interaction.edit_original_message(
                    content=f"That's cool. Use `/chess ready` whenever you're ready.",
                    view=None,
                    embeds=[]
                )

    @chess_group.command(description="Make a move in a chess match.")
    @chess.helpers.verify_context(level="turn")
    async def move(self,
                   ctx: discord.ApplicationContext,
                   notation: Option(str, name="move",
                                    description="Specify a move using algebraic or UCI notation. "
                                                "If you're confused, leave this blank.",
                                    required=False)):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)

        if notation:
            await player.move_with_notation(ctx, notation)
        else:
            await player.move_with_gui(ctx)

    @chess_group.command(description="View the board in a chess match.")
    @chess.helpers.verify_context(level="game")
    async def board(self, ctx: discord.ApplicationContext):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)

        await player.view_board(ctx)

    @chess_group.command(description="Forfeit a chess match.")
    @chess.helpers.verify_context(level="player")
    async def forfeit(self, ctx: discord.ApplicationContext):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)

        if chess_game.has_started:
            msg = f"Forfeiting will cause {player.opponent.user.mention} to be declared the winner. " \
                  f"If this outcome is not desirable, consider proposing a draw instead.\n" \
                  "\n" \
                  "This can't be undone.\n" \
                  "\n" \
                  "" \
                  "Forfeit this match?"
        else:
            msg = "Forfeiting will immediately end the match for both you and your opponent. This can't be undone.\n" \
                  "\n" \
                  "Forfeit this match?"

        embed = discord.Embed(title="Are you sure?", description=msg, color=support.Color.orange())

        view = support.ConfirmationView(ctx=ctx)

        confirmation = await view.request_confirmation(prompt_embeds=[embed], ephemeral=True)

        if confirmation:
            await ctx.interaction.edit_original_message(content="Forfeiting the match...", view=None, embeds=[])
            await player.forfeit()
        else:
            await ctx.interaction.edit_original_message(content=f"Okay! The game is still on.", view=None, embeds=[])

    @chess_group.command(description="Propose a draw in a chess match, or rescind a proposal you've already made.")
    @chess.helpers.verify_context(level="game")
    async def draw(self,
                   ctx: discord.ApplicationContext,
                   mode: Option(str, description="Choose whether to propose a draw or rescind an existing proposal.",
                                choices=["Propose", "Rescind"])):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(ctx.channel.id)
        player: chess.ChessPlayer = chess_game.retrieve_player(ctx.user)
        if mode == "Propose":
            if player.has_proposed_draw:
                msg = "You'll need to resicind your current proposal before you can make a new one."
                embed = discord.Embed(title="You've already proposed a draw.",
                                      description=msg, color=support.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)
            else:
                msg = f"If you think it's time to wrap things up, you can propose a draw. If " \
                      f"{player.opponent.user.mention} accepts, the match will end in a draw, with neither player " \
                      f"being declared the winner.\n" \
                      "\n" \
                      "If you change your mind before your opponent accepts your proposal, you can rescind your " \
                      "proposal by using `/chess draw` and selecting the 'Rescind' option.\n" \
                      "\n" \
                      "Propose a draw?"

                embed = discord.Embed(title="Proposing a Draw", description=msg, color=support.Color.orange())

                view = support.ConfirmationView(ctx=ctx)

                confirmation = await view.request_confirmation(prompt_embeds=[embed], ephemeral=True)

                if confirmation:
                    await ctx.interaction.edit_original_message(content="Proposing a draw...", view=None, embeds=[])
                    await player.propose_draw()
                else:
                    await ctx.interaction.edit_original_message(
                        content=f"Okay! You can propose a draw at any time if you change your mind.",
                        view=None, embeds=[])
        elif mode == "Rescind":
            if not player.has_proposed_draw:
                msg = "You need to propose a draw before you can rescind one."
                embed = discord.Embed(title="You haven't proposed a draw.", description=msg, color=support.Color.red())

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

        if (chess_game and not chess_game.retrieve_player(message.author) and not message.author.bot and
                not support.helpers.is_celsius_narhwal(message.author)):
            await message.delete()

    @commands.Cog.listener(name="on_thread_member_remove")
    async def sync_game_thread_removal(self, thread_member: discord.ThreadMember):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(thread_member.thread_id)
        player: chess.ChessPlayer = chess_game.retrieve_player(thread_member)

        if player:
            await player.forfeit()

            msg = f"I forfeited your chess match against {player.opponent.user.mention} in {chess_game.guild} " \
                  f"on your behalf because you left the game thread."

            embed = discord.Embed(title="Chess Match Forfeited", description=msg, color=support.Color.red(),
                                  timestamp=discord.utils.utcnow())

            await player.user.send(embed=embed)

    @commands.Cog.listener(name="on_raw_thread_delete")
    async def force_close_thread_deletion(self, thread: discord.RawThreadDeleteEvent):
        chess_game: chess.ChessGame = chess.ChessGame.retrieve_game(thread.thread_id)

        if chess_game:
            await chess_game.force_close(reason="thread_deletion")

    @commands.Cog.listener(name="on_guild_channel_delete")
    async def force_close_channel_deletion(self, channel):
        for thread in [thread for thread in channel.threads if chess.ChessGame.retrieve_game(thread.id)]:
            chess_game = chess.ChessGame.retrieve_game(thread.id)
            await chess_game.force_close(reason="channel_deletion")
