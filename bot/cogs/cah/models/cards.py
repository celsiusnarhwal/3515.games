########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import copy
import random
import re
import uuid

import aiohttp
import discord
import orjson
from attrs import define
from elysia import Fields
from llist import dllist, dllistnode
from ordered_set import OrderedSet
from pydantic import BaseModel, Field, validate_arguments, validator

from cogs.cah.models.player import CAHPlayer
from keyboard import *
from support import NLP


class CAHBlackCard(BaseModel):
    """
    A black card.
    """

    class Config:
        frozen = True

    text: Optional[str]  # not actually optional
    pick: int

    @validator("text")
    def normalize_text(cls, v):
        if "_" not in v:
            v += " _"

        return discord.utils.escape_markdown(v.replace("_", "_" * 5))

    @validator("text")
    def no_haiku(self, v):
        if v == "Make a haiku.":
            return None

    def __bool__(self):
        return bool(self.text)

    def __str__(self):
        return self.text


class CAHWhiteCard(BaseModel):
    """
    A white card.
    """

    class Config:
        frozen = True

    text: Optional[str]  # not actually optional
    uuid: str = Field(default_factory=lambda: uuid.uuid4().hex, const=True)

    @validator("text", pre=True)
    def normalize(cls, v):
        if len(normalized := re.sub(r"\b$", ".", v[0].upper() + v[1:])) <= 60:
            return normalized

    def __str__(self):
        return self.text

    def __bool__(self):
        return bool(self.text)


class CAHDeck(BaseModel):
    """
    A deck of black and white cards.
    """

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"

    black: OrderedSet[CAHBlackCard]
    white: OrderedSet[CAHWhiteCard]
    backup: CAHDeck = None

    @validator("black", "white")
    def cast(cls, v):
        return OrderedSet(filter(None, v))

    @validator("backup", always=True)
    def create_backup(cls, v, values):
        if v is None:
            return cls.construct(**copy.deepcopy(values))

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
                "https://restagainsthumanity.com/api/v2/cards", params={"packs": packs}
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
    A candidate card.

    A candidate card is the combination of a black card and one or more player-selected white cards.
    """

    text: str
    player: CAHPlayer
    white_cards: list[str]

    voters: list[CAHPlayer] = Fields.attr(factory=list, on_setattr=Fields.setters.NO_OP)
    uuid: str = Fields.attr(factory=lambda: uuid.uuid4().hex)

    @classmethod
    @validate_arguments(config=dict(arbitrary_types_allowed=True))
    def create(cls, player: CAHPlayer, *white_cards: CAHWhiteCard) -> list[Self]:
        """
        Create candidate cards.

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
            for token in NLP(card.text):
                if token.pos_ == "PROPN":
                    proper_nouns.append(token.text)

        black_card = player.game.black_card

        for c1, c2 in zip(white_cards, reversed(white_cards)):
            tokens = dllist(re.split(r"((?:\\_){5})", black_card.text))

            if not tokens[-1]:
                tokens.pop()

            for card in c1, c2:
                text = card.text

                if underscores in tokens:
                    underscore_node: dllistnode = tokens.nodeat(
                        [*tokens].index(underscores)
                    )

                    strip: bool = (
                        underscore_node.prev is None or underscore_node.next is not None
                    )

                    decapitalize: bool = (
                        underscore_node.prev is not None
                        and bool(underscore_node.prev.value)
                        and not underscore_node.prev.value.rstrip().endswith(
                            tuple(punctuation)
                        )
                        and not text.istitle()
                        and text.split()[0] not in proper_nouns
                    )

                    if strip:
                        text = text.rstrip(punctuation)

                    if decapitalize:
                        text = text[0].lower() + text[1:]

                    tokens.insertbefore(f"**{text}**", underscore_node)
                    tokens.remove(underscore_node)

            candidates.append(cls("".join(tokens), player, white_cards))

            if len(candidates) == black_card.pick:
                break

        return candidates

    def __str__(self):
        return self.text
