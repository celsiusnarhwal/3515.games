from __future__ import annotations

import discord
from llist import sllist as LinkedList, sllistnode

import support
from support import HostedMultiplayerGame, posessive


class CAHGame(HostedMultiplayerGame):
    __all_games__ = dict()

    def __init__(self, guild: discord.Guild, thread: discord.Thread, host: discord.User, cards: dict,
                 settings: CAHGameSettings):

        self.name = "Cards Against Humanity"

        super().__init__(guild, thread, host)
        self.cards = cards
        self.settings: CAHGameSettings = settings

        self.players = LinkedList()
        self.banned_users = set()
        self.current_players = sllistnode()
        self.turn_uuid = None
        self.black_card: dict = None
        self.lobby_intro_msg: discord.Message = None

        self.__all_games__[self.thread.id] = self

    async def open_lobby(self):
        """
        Sends an introductory message at the creation of an CAH game thread and pins said message to that thread.
        """
        intro_message = f"{self.host.mention} is the Game Host.\n" \
                        f"\n" \
                        f"To **join**, type `/uno join`. \n" \
                        f"\n" \
                        f"To **spectate**, you don't have to do anything! Anyone can spectate " \
                        f"by simply being in the thread.\n" \
                        f"\n" \
                        f"@everyone mentions will be used to notify players of important game events. Players are " \
                        f"advised to make sure their notification settings for this server are __not__ set to " \
                        f"suppress @everyone mentions.\n" \
                        f"\n" \
                        f"If you're a spectator, you'll also be pinged by these " \
                        f"@everyone mentions. If that's a problem, you'll have to either suppress @everyone mentions " \
                        f"in your notification settings for this server or stop spectating and leave the thread.\n" \
                        f"\n" \
                        f"The Game Host can begin the game at any time with `/cah host start`. Once the game " \
                        f"has begun, no new players will be able to join."

        intro_embed = discord.Embed(title=f"Welcome to {posessive(self.host.name)} Cards Against Humanity game!",
                                    description=intro_message,
                                    color=support.Color.mint())

        settings_embed = discord.Embed(title="Game Settings", description=str(self.settings),
                                       color=support.Color.mint())

        self.lobby_intro_msg = await self.thread.send(embeds=[intro_embed, settings_embed])
        await self.lobby_intro_msg.pin()


class CAHGameSettings:
    def __init__(self, max_players: int, points_to_win: int, timeout: int, use_czar: bool):
        self.max_players = max_players
        self.points_to_win = points_to_win
        self.timeout = timeout
        self.use_czar = use_czar

    def __str__(self):
        players_str = f"__**Maximum Players**: {self.max_players}__\n" \
                      f"Up to {self.max_players} can join this CAH game. Once that quota is filled," \
                      f"no one else will be able to join unless a player leaves or is removed by the Game Host."

        points_str = f"__**Points to Win**: {self.points_to_win}__\n" \
                     f"The first player to reach {self.points_to_win} points will win the game."

        timeout_str = f"__**Timeout**: {self.timeout} seconds__\n" \
                      f"Each player will have {self.timeout} seconds to play white cards when prompted. " \
                      f"When it's voting time, {'the Card Czar' if self.use_czar else 'players'} will have " \
                      f"{self.timeout} seconds to vote for a white card."

        voting_str = f"__**Voting Mode**: {'Card Czar' if self.use_czar else 'Popular Vote'}__\n" \
                     f"At the end of each round, the funniest white card will be decided by " \
                     f"{'a Card Czar' if self.use_czar else 'popular vote'}."

        return "\n\n".join([players_str, points_str, timeout_str, voting_str])
