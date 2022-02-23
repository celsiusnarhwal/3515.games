from discord import ButtonStyle
from discord.ext import pages


def paginator_emoji_buttons(button_style: ButtonStyle = ButtonStyle.blurple):
    return [
        pages.PaginatorButton("first", emoji="⏮", style=button_style),
        pages.PaginatorButton("prev", emoji="⏪", style=button_style),
        pages.PaginatorButton("page_indicator", style=ButtonStyle.gray, disabled=True),
        pages.PaginatorButton("next", emoji="⏩", style=button_style),
        pages.PaginatorButton("last", emoji="⏭", style=button_style)
    ]
