########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from path import Path


class Routes(Path):
    """
    A reliable accessor for certain top-level directories.
    """

    @classmethod
    def root(cls):
        return cls(__file__).parent

    @classmethod
    def bot(cls):
        return cls.root() / "bot"

    @classmethod
    def kurisu(cls):
        return cls.root() / "kurisu"
