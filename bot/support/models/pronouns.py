########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from enum import StrEnum, auto

import inflect as ifl
from ordered_set import OrderedSet
from pydantic import validate_arguments

from keyboard import *

inflect = ifl.engine()


class Gender(StrEnum):
    MASCULINE = auto()
    FEMININE = auto()
    NEUTER = auto()
    NEUTRAL = "gender-neutral"

    @classmethod
    def decode(cls, code: str) -> OrderedSet[Self]:
        match code:
            case "any":
                return OrderedSet(cls)
            case "shh":
                return OrderedSet([cls.MASCULINE, cls.FEMININE])
            case "sh":
                return OrderedSet([cls.FEMININE])
            case _ if len(code) == 2:
                bitmap = {
                    "s": cls.FEMININE,
                    "h": cls.MASCULINE,
                    "i": cls.NEUTER,
                    "t": cls.NEUTRAL,
                }

                return OrderedSet([bitmap[bit] for bit in code])
            case _:
                return OrderedSet([cls.NEUTRAL])


class Pronoun(StrEnum):
    THEY = auto()
    THEM = auto()
    THEIR = auto()
    THEIRS = auto()
    THEMSELVES = auto()

    @validate_arguments
    def transform(self, gender: Gender) -> str:
        match self:
            case self.THEIR:
                return {
                    Gender.MASCULINE: "his",
                    Gender.FEMININE: "her",
                    Gender.NEUTER: "its",
                }.get(gender, self.value)
            case self.THEMSELVES if gender is Gender.NEUTRAL:
                return self.value
            case _:
                return inflect.singular_noun(self.value, gender=gender.value)
