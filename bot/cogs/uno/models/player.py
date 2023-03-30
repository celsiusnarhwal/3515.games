########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import discord
from attr import define
from discord.ext import pages as discord_pages
from sortedcontainers import SortedKeyList

import support
from cogs import uno
from support import BasePlayer, PlayerVoiceMixin


@define(slots=False)
class UnoPlayer(PlayerVoiceMixin, BasePlayer):
    """
    A player in an UNO game.

    Parameters
    ----------
    user: :class:`discord.Member`
        The associated Discord user.
    game: :class:`cogs.uno.models.game.UnoGame`
        The associated game.

    Attributes
    ----------
    points: :class:`int`
        The number of points the player has.
    hand : :class:`SortedKeyList[UnoCard]`
        The cards in the player's posession.
    can_say_uno: :class:`bool`
        Whether the player can say "UNO!".
    has_said_uno: :class:`bool`
        Whether the player has said "UNO!" in the time since their hand was most recently reduced to one card.
    terminable_views : :class:`list[support.View]`
        A list of :class:`uno.views.UnoTerminableView` instances that the player has created.
    timeout_counter: :class:`int`
        The number of consecutive turns on which the player has timed out.
    """

    user: discord.Member
    game: uno.UnoGame

    def __attrs_post_init__(self):
        super().__attrs_post_init__()

        self.points: int = 0
        self.hand: SortedKeyList[uno.UnoCard] = SortedKeyList(
            key=lambda card: card.sortcode
        )
        self.can_say_uno = False
        self.has_said_uno = False
        self.terminable_views: list[uno.UnoTerminableView] = []
        self.timeout_counter: int = 0

        # for uno status center
        self.num_cards_played = 0
        self._num_cards_drawn = 0

    async def show_hand(self, ctx: discord.ApplicationContext):
        """
        Shows the player the cards they're currently holding.

        :param ctx: A discord.ApplicationContext object.
        """
        split_cards = support.split_list(self.hand, 23)
        pages = [
            discord.Embed(
                title="Your Hand",
                description=f"Here are all the cards you're currently holding:\n\n"
                f"{chr(10).join([f'- {str(card)} {card.emoji}' for card in page])}",
                color=support.Color.mint(),
            )
            for page in split_cards
        ]

        for embed in pages:
            embed.set_footer(
                text=discord.utils.remove_markdown(self.game.last_move_str)
            )

        paginator = discord_pages.Paginator(
            pages=pages,
            use_default_buttons=False,
            custom_buttons=support.pagimoji(),
        )

        await paginator.respond(ctx.interaction, ephemeral=True)

    async def select_card(self, ctx: discord.ApplicationContext):
        """
        Allows players to select a card to play.

        :param ctx: A discord.ApplicationContext object.
        turn.
        """

        view = uno.UnoCardSelectView(ctx=ctx, player=self, cards=self.hand)
        selected_card: uno.UnoCard = await view.select_card()

        if selected_card:
            # inform the player about saying 'UNO!' if playing the card will leave them with only one card in their hand
            if len(self.hand) == 2:
                msg = (
                    'After playing this card, you"re required to say "UNO!" `(/uno play > "Say UNO!")` or risk '
                    "being called out by other players.\n"
                    "\n"
                    "Play this card?"
                )
                embed = discord.Embed(
                    title="One Card Remaining",
                    description=msg,
                    color=support.Color.caution(),
                )

                view = uno.UnoTerminableConfView(ctx=ctx)
                confirmation = await view.request_confirmation(
                    prompt_embeds=[embed], ephemeral=True, edit=True
                )

                if confirmation:
                    if selected_card.color is not uno.UnoCardColor.WILD:
                        await ctx.interaction.edit_original_response(
                            content="Good luck! 🤞🏾", embeds=[], view=None
                        )
                else:
                    await ctx.interaction.edit_original_response(
                        content="Okay! Make your move whenever you're ready.",
                        embeds=[],
                        view=None,
                    )

                    return

            # present color selection view if the player selects a wild card, provided it isn't the last card in
            # their hand
            if selected_card.color is uno.UnoCardColor.WILD and len(self.hand) > 1:
                view = uno.WildColorSelectView(ctx=ctx, player=self, card=selected_card)
                selected_card = await view.choose_color()

                if selected_card.transformation:
                    # only play the card if the player selected a color
                    await self.play_card(selected_card)
            else:
                await self.play_card(selected_card)

    async def play_card(self, card: uno.UnoCard, with_draw: bool = False):
        """
        Play an UNO card.

        Parameters
        ----------
        card: :class:`UnoCard`
            The card to play.
        with_draw: :class:`bool`
            Whether the card is being played automatically after being drawn.
        """
        await self.reset_timeouts()

        # remove the card from the player's hand
        self.hand.remove(card)
        self.num_cards_played += 1

        await self.game.processor.card_played_event(
            player=self, card=card, with_draw=with_draw
        )

        await self.end_turn()

    async def draw_card(self, ctx: discord.ApplicationContext):
        """
        Draws an UNO card.

        Parameters
        ----------
        ctx: :class:`discord.ApplicationContext`
        """

        view = uno.UnoDrawCardView(ctx=ctx)
        await view.draw_card()

        if view.success:
            await self.reset_timeouts()

            drawn_card = await self.add_cards(1)

            card = drawn_card[0]

            if (
                view.autoplay
                and self.game.is_card_playable(card)
                and card.color is not uno.UnoCardColor.WILD
            ):
                # play the card if it can be played on the current turn and isn't a wild or wild draw four
                embed = discord.Embed(
                    title="Card Drawn and Played",
                    description=f"You drew and played a **{str(card)}**.",
                    color=card.embed_color,
                )
                embed.set_thumbnail(url=card.emoji.url)

                await ctx.interaction.edit_original_response(embeds=[embed], view=None)

                if len(self.hand) - 1 == 1:
                    embed = discord.Embed(
                        title="One Card Remaining",
                        description="You'll need to say 'UNO!' or risk being called out by "
                        "other players.",
                        color=support.Color.caution(),
                    )

                    await ctx.interaction.followup.send(embed=embed, ephemeral=True)

                await self.play_card(card, with_draw=True)
            else:
                embed = discord.Embed(
                    title="Card Drawn",
                    description=f"You drew a **{str(card)}**.",
                    color=card.embed_color,
                )
                embed.set_thumbnail(url=card.emoji.url)

                await ctx.interaction.edit_original_response(embeds=[embed], view=None)

                await self.game.processor.card_drawn_event(player=self)

                await self.end_turn()
        elif view.success is False:
            msg = "Okay! Make your move whenever you're ready."
            await ctx.interaction.edit_original_response(
                content=msg, embeds=[], view=None
            )

    async def say_uno(self):
        """
        Say 'UNO!'.
        """
        await self.game.processor.say_uno_event(player=self)

    async def callout(self, ctx: discord.ApplicationContext):
        """
        Call out a player for having one remaining card and failing to say 'UNO!'.

        Parameters
        ----------
        ctx: :class:`discord.ApplicationContext`
        """
        target = await uno.UnoCalloutView(ctx=ctx).present()

        if target.can_say_uno and not target.has_said_uno:
            embed = discord.Embed(
                title="The callout succeeds!",
                description=f"{target.user.name} draws two cards.",
                color=support.Color.green(),
            )

            await ctx.interaction.edit_original_response(embeds=[embed], view=None)
            await self.game.processor.callout_event(
                challenger=self, target=target, callout_success=True
            )
        else:
            embed = discord.Embed(
                title="The callout fails.",
                description="You draw a card and forfeit your turn.",
                color=support.Color.brand_red(),
            )

            await ctx.interaction.edit_original_response(embeds=[embed], view=None)
            await self.game.processor.callout_event(
                challenger=self, target=target, callout_success=False
            )
            await self.end_turn()

    async def add_cards(self, num_cards):
        """
        Add cards to the player's hand.

        Parameters
        ----------
        num_cards: :class:`int`
            The number of cards to add.
        """
        new_cards = uno.UnoCard.generate_cards(num_cards)

        self.num_cards_drawn += num_cards

        self.hand.update(new_cards)

        self.can_say_uno = False
        self.has_said_uno = False

        return new_cards

    async def reset_timeouts(self):
        """
        Resets the player's timeout counter to 0.
        """
        self.timeout_counter = 0

    async def end_turn(self):
        """
        Ends the player's turn.
        """
        for view in self.terminable_views:
            if not view.is_finished():
                await view.full_stop()

        if len(self.hand) == 1 and not self.has_said_uno:
            self.can_say_uno = True

        await self.game.end_turn()

        self.terminable_views.clear()

    @property
    def hand_value(self):
        """
        The collective value of all cards in the player's hand.

        See Also
        --------
        :attr:`UnoCard.point_value`
        """
        return sum(card.point_value for card in self.hand)

    @property
    def num_cards_drawn(self):
        """
        The total number of cards the player has drawn.

        Notes
        -----
        This is defined as a property rather than a normal instance attribute so that its value can be
        dynamically altered to exclude the seven cards dealt to each player at the start of a round.
        """
        # where d1 includes dealt cards and d2 does not:
        # d2 = d1 - (7 * round_number) OR d2 = 0, whichever is higher
        return max(self._num_cards_drawn - (7 * self.game.current_round), 0)

    @num_cards_drawn.setter
    def num_cards_drawn(self, value):
        self._num_cards_drawn += value

    def __str__(self):
        return self.user.name
