from typing import Union

import discord.ui
from discord import Interaction
from discord.ui import Button, Select

import support
from cogs import uno
from support.views import EnhancedView


#
# class CardSelectionDropdown(discord.ui.Select):
#     def __init__(self, cards: list[uno.UnoCard]):
#         super(CardSelectionDropdown, self).__init__(
#             placeholder="Pick a card, any card",
#             min_values=1,
#             max_values=2
#         )
#
#         for card in cards:
#             self.add_option(label=card.__str__(), emoji=card.emote)
#
#     async def callback(self, interaction: Interaction):
#         self.


class GoToUnoThreadView(EnhancedView):
    def __init__(self, thread_url, **kwargs):
        super(GoToUnoThreadView, self).__init__(**kwargs)
        self.add_item(Button(label="Go to game thread", url=thread_url))


# TODO consider allowing for the manipulation of this view in uno/classes.py
class UnoPlayCardView(EnhancedView):
    def __init__(self, player: uno.UnoPlayer, **kwargs):
        super(UnoPlayCardView, self).__init__(**kwargs)
        self.player = player
        self.timeout = 90

    async def on_timeout(self) -> None:
        self.clear_items()
        timeout_embed = discord.Embed(title="Timeout Error", description="You took too long to make a selection.",
                                      color=discord.Color.red())
        await self.ctx.edit(content=None, embed=timeout_embed, view=self)

    async def interaction_check(self, interaction: Interaction) -> bool:
        card_menu: Select = next(child for child in self.children if isinstance(child, Select))
        played_card: uno.UnoCard = discord.utils.find(lambda x: x["uuid"] == card_menu.values[0],
                                                      self.player.hand)["card"]

        if self.player != self.player.game.current_player.value:
            msg = "You can only do that when it's your turn. Wait your turn, try again."
            embed = discord.Embed(title="It's not your turn.", description=msg, color=support.ExtendedColors.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif not self.player.game.verify_card_playability(played_card):
            msg = "You can only play a card that matches the color or suit of the last card played. " \
                  "Pick a different card, or draw a card with `/uno draw` if there are no cards you can play."
            embed = discord.Embed(title="You can't play that card.", description=msg,
                                  color=support.ExtendedColors.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            for child in self.children:
                child.disabled = True

            self.stop()
            self.success = True
            return await super(UnoPlayCardView, self).interaction_check(interaction)

    async def select_card(self) -> Union[uno.UnoCard, None]:
        card_menu = Select(
            placeholder="Pick a card, any card!",
            min_values=1,
            max_values=1,
        )

        # TODO add interaction_check validation (e.g. current turn, card playability)
        for card in self.player.hand:
            card_menu.append_option(
                discord.SelectOption(label=card["card"].__str__(), emoji=card["card"].emoji, value=card["uuid"]))

        self.add_item(card_menu)

        msg = "Pick a card from the dropdown menu. You can play any card that matches the color or suit of the " \
              "last card played. You can also play a Wild or Wild Draw Four card, if you have one."
        embed = discord.Embed(title="Play a Card", description=msg, color=support.ExtendedColors.mint())
        prompt = await self.ctx.respond(embed=embed, view=self, ephemeral=True)

        await self.wait()

        if self.success:
            await prompt.edit_original_message(view=self)
            card_dict = discord.utils.find(lambda x: x["uuid"] == card_menu.values[0], self.player.hand)
            self.player.hand.remove(card_dict)
            return card_dict["card"]
        else:
            return None
