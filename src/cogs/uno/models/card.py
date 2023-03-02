########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import random
import string
import uuid
from enum import Enum, EnumMeta

import discord
import tomlkit as toml
from attrs import define
from dict_deep import deep_get

import support
from keyboard import *
from support import Fields

__all__ = ["UnoCard", "UnoCardColor", "UnoCardSuit"]


class UnoCardAttrMeta(EnumMeta):
    """
    Metaclass for :class:`UnoCardAttr`.
    """

    def iterd(cls):
        """
        Iterate over all non-special attributes.

        Notes
        -----
        Equivalent to :meth:`__iter__`, which simply returns this method's result.
        """
        for attr in super().__iter__():
            if attr not in cls._special:
                yield attr

    def iters(cls):
        """
        Iterate over all special attributes.
        """
        for attr in super().__iter__():
            if attr in cls._special:
                yield attr

    def itera(cls):
        """
        Iterate over all attributes.
        """
        return super().__iter__()

    def index(cls, value):
        """
        Get the index of the given attribute within its enumeration.

        Parameters
        ----------
        value : UnoCardAttr
            The attribute to get the index of.

        Returns
        -------
        int
            The index of the attribute.
        """
        return list(cls.itera()).index(value)

    @property
    def _special(cls):
        return UnoCardColor.WILD, UnoCardSuit.DRAW_FOUR, UnoCardSuit.NONE

    def __iter__(self):
        return self.iterd()


class UnoCardAttr(Enum, metaclass=UnoCardAttrMeta):
    """
    Base enumeration for :class:`UnoCardColor` and :class:`UnoCardSuit`.
    """

    def casefold(self):  # temporary backwards-compatibility patch; remove eventually
        return str(self).casefold()

    @property
    def emoji_key(self):
        return self.name.lower()

    @property
    def sortcode(self):
        return type(self).index(self)

    def __str__(self):
        return str(self.value).title()


class UnoCardColor(UnoCardAttr):
    """
    Enumerates UNO card colors.
    """

    # Default
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"

    # Special
    WILD = "wild"


class UnoCardSuit(UnoCardAttr):
    """
    Enumerates UNO card suits.
    """

    # Default
    ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE = string.digits
    REVERSE = "reverse"
    SKIP = "skip"
    DRAW_TWO = "+2"

    # Special
    NONE = None
    DRAW_FOUR = "+4"

    def __bool__(self):
        return self is not self.NONE


@define(on_setattr=Fields.setters.frozen)
class UnoCard:
    """
    An UNO card.

    Parameters
    ----------
    color: :class:`UnoCardColor`
        The color of the card.
    suit: :class:`UnoCardSuit`
        The suit of the card.
    """

    canonical: ClassVar = [
        *[[color, suit] for color in UnoCardColor for suit in UnoCardSuit],
        [UnoCardColor.WILD],
        [UnoCardColor.WILD, UnoCardSuit.DRAW_FOUR],
    ]

    color: UnoCardColor
    suit: UnoCardSuit = UnoCardSuit.NONE

    transformation: UnoCardColor = Fields.attr(
        default=None,
        on_setattr=Fields.setters.validate,
        validator=Fields.validators.optional(
            Fields.validators.instance_of(UnoCardColor)
        ),
    )
    uuid: str = Fields.attr(factory=lambda: uuid.uuid4().hex)

    # noinspection PyUnresolvedReferences
    @transformation.validator
    def validate(self, _, value):
        if self.color is not UnoCardColor.WILD and value is not None:
            raise ValueError("transformation can only be set on Wild cards")

    @classmethod
    def generate_cards(cls, num_cards) -> list[UnoCard]:
        """
        Generate UNO cards of random canonical color-suit combinations.

        Parameters
        ----------
        num_cards
            The number of cards to generate.

        Returns
        -------
        :class:`list` of :class:`UnoCard`
            The generated cards.
        """
        return [cls(*card) for card in random.choices(cls.canonical, k=num_cards)]

    @property
    def versus_color(self) -> UnoCardColor:
        """
        The color to be used when checking if this card is playable against another.
        """
        return self.transformation or self.color

    @property
    def versus_suit(self) -> UnoCardSuit:
        """
        The suit to be used when checking if this card is playable against another.

        Notes
        -----
        This property is equivalent to :attr:`UnoCard.suit` and exists only for consistency with
        :attr:`UnoCard.versus_color`.
        """
        return self.suit

    @property
    def emoji(self) -> discord.PartialEmoji:
        """
        The card's corresponding Discord emoji.
        """
        with support.Assets.uno():
            emoji = toml.load(open("uno_card_emotes.toml"))
            return discord.PartialEmoji.from_str(deep_get(emoji, self.emoji_key))

    @property
    def emoji_key(self) -> str:
        """
        The card's emoji key.
        """
        return f"{self.color.emoji_key}.{self.suit.emoji_key}"

    @property
    def point_value(self) -> int:
        """
        The card's point value.
        """

        # wild and wild draw four cards are worth 50 points
        if self.color is UnoCardColor.WILD:
            return 50

        # reverse, skip, and draw two cards are worth 20 points
        elif self.suit in [UnoCardSuit.REVERSE, UnoCardSuit.SKIP, UnoCardSuit.DRAW_TWO]:
            return 20

        # otherwise, it's a numbered card and worth its face value
        else:
            return int(self.suit.value)

    @property
    def embed_color(self) -> support.Color:
        """
        The card's corresponding embed color.
        """

        embed_colors = {
            UnoCardColor.RED: support.Color.brand_red(),
            UnoCardColor.BLUE: support.Color.blue(),
            UnoCardColor.GREEN: support.Color.green(),
            UnoCardColor.YELLOW: support.Color.yellow(),
            UnoCardColor.WILD: support.Color.black(),
        }

        return embed_colors[self.color]

    @property
    def transformation_embed_color(self) -> support.Color:
        """
        The embed color corresponding to the card's transformation. Only applicable to Wild cards.
        """
        if self.color is not UnoCardColor.WILD:
            raise ValueError(
                "transformation_embed_color may only be accessed on Wild cards"
            )

        if not self.transformation:
            raise ValueError(
                "transformation must be set before transformation_embed_color can be accessed"
            )

        embed_colors = {
            UnoCardColor.RED: support.Color.brand_red(),
            UnoCardColor.BLUE: support.Color.blue(),
            UnoCardColor.GREEN: support.Color.green(),
            UnoCardColor.YELLOW: support.Color.yellow(),
        }

        return embed_colors[self.transformation]

    @property
    def sortcode(self) -> int:
        """
        An integer to be used as a key when sorting this card among others.

        Enforces sorting by color in order of:
            RED, BLUE, GREEN, YELLOW, WILD
        and then by suit in order of:
            ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE, REVERSE, SKIP, DRAW_TWO, NONE, DRAW_FOUR
        where each color and suit corresponds to a member of :class:`UnoCardColor` and :class:`UnoCardSuit`,
        respectively.

        Returns
        -------
        :class:`int`
            The card's sort code.
        """
        return self.color.sortcode * 100 + self.suit.sortcode

    def __str__(self):
        return f"{self.color} {self.suit}" if self.suit else str(self.color)
