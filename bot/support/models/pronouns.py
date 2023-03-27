from __future__ import annotations

from enum import StrEnum, auto


class Pronoun(StrEnum):
    THEY = auto()
    THEM = auto()
    THEIR = auto()
    THEIRS = auto()
    THEMSELVES = auto()


class PronounType(StrEnum):
    MASCULINE = "m"
    FEMININE = "f"
    NEUTER = "n"
    GENDER_NEUTRAL = "g"
