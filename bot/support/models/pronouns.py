########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from enum import StrEnum, auto

import inflect as ifl
from pydantic import validate_arguments

inflect = ifl.engine()


class Gender(StrEnum):
    MASCULINE = auto()
    FEMININE = auto()
    NEUTER = auto()
    NEUTRAL = "gender-neutral"


class Pronoun(StrEnum):
    THEY = auto()
    THEM = auto()
    THEIR = auto()
    THEIRS = auto()
    THEMSELVES = auto()

    @validate_arguments
    def transform(self, gender: Gender) -> str:
        match self:
            case Pronoun.THEIR:
                return {
                    Gender.MASCULINE: "his",
                    Gender.FEMININE: "her",
                    Gender.NEUTER: "its",
                }.get(gender, self.value)
            case Pronoun.THEMSELVES if gender is Gender.NEUTRAL:
                return self.value
            case _:
                return inflect.singular_noun(self.value, gender=gender.value)
