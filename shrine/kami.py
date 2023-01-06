########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Jinja2 template filters and globals.
"""

import inflect as ifl

from shrine import torii


@torii.register_filter
def deline(content: str) -> str:
    """
    Replace all newlines in a string with spaces.

    Parameters
    ----------
    content : str
        The string.

    Returns
    -------
    str
        The modified string.

    Notes
    -----
    This filter intends to mitigate the effects of Discord's treatment of carriage returns as newlines.
    """
    return content.replace("\n", " ")


@torii.register_global(call=True)
def inflect() -> ifl.engine:
    """
    Return an inflect engine.

    Notes
    -----
    This essentially makes the entire inflect module available to templates rendered by :class:`shrine.torii.Torii`.
    """
    return ifl.engine()
