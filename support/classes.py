import discord


class ExtendedColors(discord.Color):
    """
    An extension of Pycord's ``discord.Color`` class that implements additional colors not included with the library.
    Because it subclasses ``discord.Color``, both the standard Pycord colors and the custom colors implemented
    by this class can be accessed from ``ExtendedColors`` objects, avoiding the need to flip-flop between
    ``ExtendedColors`` and ``discord.Color``.
    """
    def __init__(self, value):
        super(ExtendedColors, self).__init__(value)

    @classmethod
    def mint(cls):
        return cls(0x03cb98)

    @classmethod
    def cyan(cls):
        return cls(0x00ffff)
