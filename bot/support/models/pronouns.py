########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

from enum import StrEnum, auto


class Pronoun(StrEnum):
    THEY = auto()
    THEM = auto()
    THEIR = auto()
    THEIRS = auto()
    THEMSELVES = auto()


class PronounType(StrEnum):
    MASCULINE = auto()
    FEMININE = auto()
    NEUTER = auto()
    GENDER_NEUTRAL = "gender-neutral"
