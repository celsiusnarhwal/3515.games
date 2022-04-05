import discord
from discord import Interaction, ButtonStyle
from discord.ext import pages as discord_pages
from discord.ui import Button, button as discord_button

import support
from cogs.rps import rps
from support.views import EnhancedView


class RPSChooseMoveView(EnhancedView):
    """
    Provides the user interface for players in a Rock-Paper-Scissors match to choose their moves. This view only
    accepts interactions from the users playing in the match and will persist until either both players have chosen
    a move or the view times out, whichever is sooner.
    """

    def __init__(self, players: list[rps.RPSPlayer], **kwargs):
        """
        The constructor for ``RPSChooseMoveView``.

        :param players: A list of players in the match.
        """
        super().__init__(**kwargs)
        self.ready_players = set()
        self.players = players
        self.challenger = players[0].user
        self.opponent = players[1].user
        self.timeout = 60

    async def on_timeout(self):
        timeout_message = "Your Rock-Paper-Scissors match has been aborted because one of you took too long to make a " \
                          "move. You can start another match with `/rps start.`"
        timeout_embed = discord.Embed(title="You timed out.", description=timeout_message,
                                      color=discord.Color.red())
        await self.ctx.send(f"{self.challenger.mention} {self.opponent.mention}",
                            embed=timeout_embed)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user not in [self.challenger, self.opponent]:
            await interaction.response.send_message("You can't do that.", ephemeral=True)
        elif [player for player in self.ready_players if player.user == interaction.user]:
            await interaction.response.send_message(
                f"You've already chosen your move. "
                f"Wait for {self.challenger.mention if interaction.user == self.opponent else self.opponent.mention} "
                f"to choose theirs.",
                ephemeral=True)
        else:
            return await super().interaction_check(interaction)

    @discord_button(label="Rock", emoji="🪨", style=ButtonStyle.blurple)
    async def rock(self, button: Button, interaction: Interaction):
        interacting_player = next(player for player in self.players if player.user == interaction.user)
        interacting_player.selected_move = "Rock"

        self.ready_players.add(interacting_player)

        await interaction.response.send_message(
            f"You chose **🪨 Rock**. "
            f"Waiting for {self.challenger.mention if interaction.user == self.opponent else self.opponent.mention}'s "
            f"move...",
            ephemeral=True)

        if len(self.ready_players) == 2:
            self.success = True
            self.stop()

    @discord_button(label="Paper", emoji="📄", style=ButtonStyle.blurple)
    async def paper(self, button: Button, interaction: Interaction):
        interacting_player = next(player for player in self.players if player.user == interaction.user)
        interacting_player.selected_move = "Paper"

        self.ready_players.add(interacting_player)

        await interaction.response.send_message(
            f"You chose **📄 Paper**. "
            f"Waiting for {self.challenger.mention if interaction.user == self.opponent else self.opponent.mention}'s "
            f"move...",
            ephemeral=True)

        if len(self.ready_players) == 2:
            self.success = True
            self.stop()

    @discord_button(label="Scissors", emoji="✂", style=ButtonStyle.blurple)
    async def scissors(self, button: Button, interaction: Interaction):
        interacting_player = next(player for player in self.players if player.user == interaction.user)
        interacting_player.selected_move = "Scissors"
        self.ready_players.add(interacting_player)

        await interaction.response.send_message(
            f"You chose **✂ Scissors**. "
            f"Waiting for {self.challenger.mention if interaction.user == self.opponent else self.opponent.mention}'s "
            f"move...",
            ephemeral=True)

        if len(self.ready_players) == 2:
            self.success = True
            self.stop()

    async def start_move_selection(self, round_number: int):
        """
        Initiates the move selection process.
        :param round_number: The round number.
        """
        prompt_text = f"**__Rock-Paper-Scissors__**\n" \
                      f"**{self.challenger.mention}** vs. **{self.opponent.mention}**\n" \
                      f"**Round {round_number}**" \
                      f"\n" \
                      f"Time to make your moves. What will it be?"

        prompt = await self.ctx.send(prompt_text, view=self)
        await self.wait()
        await prompt.delete()

        return self.success


class RPSMatchEndView(EnhancedView):
    """
    Provides a user interface for viewing the final results and complete record of a Rock-Paper-Scissors match.
    """
    def __init__(self, match_record: list[list[str]], **kwargs):
        """
        The constructor for ``RPSMatchEndView``.

        :param match_record: A list of lists of strings representing the match record..
        """
        super().__init__(**kwargs)
        self.match_record = match_record
        self.timeout = 180
        self.results_msg = None

    async def on_timeout(self) -> None:
        self.clear_items()
        await self.results_msg.edit(view=self)

    @discord_button(label="View Match Record", style=discord.ButtonStyle.secondary)
    async def view_match_record(self, button: Button, interaction: Interaction):
        """
        Displays the match record.
        """
        pages = [discord.Embed(title="Match Record", description="\n\n".join(page), color=support.Color.mint())
                 for page in self.match_record]
        paginator = discord_pages.Paginator(pages=pages, use_default_buttons=False,
                                            custom_buttons=support.paginator_emoji_buttons())
        await paginator.respond(interaction, ephemeral=True)

    async def show_match_results(self, players, winner):
        """
        Displays the match results.

        :param players: The players involved in the match.
        :param winner: The winner of the match.
        """
        challenger, opponent = players[0], players[1]

        results_text = f"The winner of the Rock-Paper-Scissors match between {challenger.user.mention} " \
                       f"and {opponent.user.mention} is...\n" \
                       f"\n" \
                       f"...{winner.user.mention}! " \
                       f"Congratulations!\n" \
                       f"\n" \
                       f"**Final Score:** {challenger.user.mention} {challenger.score} - " \
                       f"{opponent.score} {opponent.user.mention}\n"

        results_embed = discord.Embed(title="Rock-Paper-Scissors: Game Over!", description=results_text,
                                      color=support.Color.mint())

        self.results_msg = await self.ctx.send(embed=results_embed, view=self)
