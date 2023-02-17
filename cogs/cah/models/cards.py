########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import random
import re
import uuid

import aiohttp
import discord
import nltk
import orjson
from attrs import define
from llist import dllist, dllistnode
from ordered_set import OrderedSet
from pydantic import BaseModel, Field, validate_arguments, validator

from cogs import cah
from keyboard import *
from support import Fields


class CAHBlackCard(BaseModel):
    """
    Represents a black card in a Cards Against Humanity game.
    """

    class Config:
        frozen = True

    text: str
    pick: int

    @validator("text")
    def normalize_text(cls, v):
        if "_" not in v:
            v += " _"

        return discord.utils.escape_markdown(v.replace("_", "_" * 5))

    def __str__(self):
        return self.text


class CAHDeck(BaseModel):
    """
    Represents a set of black and white cards in a Cards Against Humanity game.
    """

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"

    black: OrderedSet[CAHBlackCard]
    white: OrderedSet[Optional[str]]  # not actually optional

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.backup = self.copy(deep=True)

    @validator("white", pre=True, each_item=True)
    def normalize_text(cls, v):
        if len(normalized := re.sub(r"\b$", ".", v[0].upper() + v[1:])) <= 60:
            return normalized

    @validator("white")
    def remove_none(cls, v):
        v.remove(None)
        return v

    # because pydantic keeps coercing these to lists for some reason???
    @validator("black", "white")
    def cast(cls, v):
        return OrderedSet(v)

    @classmethod
    @validate_arguments
    async def new(cls, *packs: str) -> Self:
        """
        Create a new deck given the exact, case-sensitive, names of one or more Cards Against Humanity packs.

        Parameters
        ----------
        packs : str
            The packs to include.

        Returns
        -------
        CAHDeck
            A new deck.

        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://restagainsthumanity.com/api", params={"packs": packs}
            ) as resp:
                if resp.status != 200:
                    raise ConnectionError

                return cls.parse_obj(await resp.json(loads=orjson.loads))

    def get_random_black(self) -> CAHBlackCard:
        """
        Return a random black card, removing it from the deck.
        """
        if not self.black:
            self.reset_black()

        return self.black.pop(random.randint(0, len(self.black) - 1))

    @validate_arguments
    def get_random_white(self, num_cards: Annotated[int, Field(ge=1)] = 1) -> set[str]:
        """
        Return a given number of random, unique, white cards, removing them from the deck.

        Parameters
        ----------
        num_cards: int, default=1
            The number of white cards to return. All white cards will be returned if this number is too big.

        Returns
        -------
        set[str]
            A set of white cards.
        """
        if num_cards > len(self.white):
            self.reset_white()
            num_cards = min(num_cards, len(self.white))

        cards = {
            self.white[i] for i in random.sample(range(len(self.white)), num_cards)
        }

        self.white.difference_update(cards)

        return cards

    def reset_black(self):
        self.black = self.backup.black.copy()

    def reset_white(self):
        self.white = self.backup.white.copy()

    def __repr__(self):
        return f"CAHDeck(black={len(self.black)}, white={len(self.white)})"

    __str__ = __repr__


@define(on_setattr=Fields.setters.frozen)
class CAHCandidateCard:
    """
    Represents a candidate card in a Cards Against Humanity game. A candidate card is a black card whose blank spaces
    have been filled by white cards.
    """

    text: str
    player: cah.CAHPlayer
    white_cards: list[str]

    voters: list[cah.CAHPlayer] = Fields.attr(
        factory=list, on_setattr=Fields.setters.NO_OP
    )
    uuid: str = Fields.attr(factory=lambda: uuid.uuid4().hex)

    @classmethod
    def make_candidates(
        cls, player: cah.CAHPlayer, *white_cards
    ) -> list[CAHCandidateCard]:
        """
        Creates candidate cards.

        Parameters
        ----------
        player: CAHPlayer
            The player who the candidate cards are being made for.
        *white_cards: str
            The white cards from which the candidate cards are being made.

        Returns
        -------
        list[CAHCandidateCard]
            The candidate cards.

        Notes
        -----
        This algorithm attempts to maintain grammatical correctness and proper noun capitalization. The enormity
        of the dataset it has to work with and the innumberable amount of possible edge cases mean it will sometimes
        produce less-than-perfect results.
        """
        # read: THIS SHIT DOESN'T WORK!!!

        candidates = []

        underscores = discord.utils.escape_markdown("_" * 5)
        punctuation = ".?!:"

        proper_nouns = []
        for card in white_cards:
            words = re.sub(r"[.?!,]", "", card).split()
            proper_nouns.extend(
                [word for word, pos in nltk.pos_tag(words) if pos.startswith("NNP")]
            )

        # ngl I shoulda written comments for this when I had the chance. too bad!

        for c1, c2 in zip(white_cards, reversed(white_cards)):
            tokens = dllist(re.split(r"((?:\\_){5})", player.game.black_card.text))
            if not tokens[-1]:
                tokens.pop()

            for card in c1, c2:
                if underscores in tokens:
                    underscore_node: dllistnode = tokens.nodeat(
                        [*tokens].index(underscores)
                    )

                    strip: bool = (
                        underscore_node.prev is None or underscore_node.next is not None
                    )

                    decapitalize: bool = (
                        underscore_node.prev is not None
                        and not underscore_node.prev.value.rstrip().endswith(
                            tuple(punctuation)
                        )
                        and card.split()[0] not in proper_nouns
                    )

                    if strip:
                        card = card.rstrip(punctuation)

                    if decapitalize:
                        card = card[0].lower() + card[1:]

                    tokens.insertbefore(f"**{card}**", underscore_node)
                    tokens.remove(underscore_node)

            candidates.append(cls("".join(tokens), player, white_cards))

            if len(candidates) == player.game.black_card.pick:
                break

        return candidates

    def __str__(self):
        return self.text
