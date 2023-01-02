########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import discord
import discord.ui
from discord import Interaction, ButtonStyle
from discord.ui import Button, button as discord_button


class EnhancedView(discord.ui.View):
    """
    A custom ``View`` class that extends Pycord's ``discord.ui.View`` class and that all of 3515.games' views inherit
    from. In addition to everything provided by ``discord.ui.View``, ``EnhancedView`` provides several useful built-in
    instance attributes which are elaborated on in the documentation for its constructor.
    """

    def __init__(
        self, ctx: discord.ApplicationContext = None, target_user: discord.User = None
    ):
        """
        The constructor for ``EnhancedView``.

        :param ctx: An ApplicationContext object. Useful to pass in if the view should perform actions in a given
            context. Optional; defaults to None.

        :param target_user: A discord.User object. Useful to pass in if the view should restrict interactions to a
            particular user. Optional; defaults to None.
        """
        super(EnhancedView, self).__init__()
        self.ctx: discord.ApplicationContext = ctx
        self.target_user: discord.User = target_user
        self.timeout = None
        self.success = None  # views can use this to indicate their successful completion (vs. timing out)

    def disable_children(self):
        for child in self.children:
            child.disabled = True

    async def full_stop(self):
        self.stop()
        self.disable_children()
        await self.ctx.interaction.edit_original_response(view=self)


class ConfirmationView(EnhancedView):
    """
    Provides a user interface for a user to confirm or cancel an action.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.timeout = None

    async def on_timeout(self) -> None:
        self.clear_items()
        timeout_embed = discord.Embed(
            title="Timeout Error",
            description="You took too long to respond.",
            color=discord.Color.red(),
        )
        await self.ctx.edit(content=None, embed=timeout_embed, view=self)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if self.target_user != interaction.user and self.target_user is not None:
            await interaction.response.send_message(
                "You can't do that.", ephemeral=True
            )
        else:
            await interaction.response.defer()
            return await super().interaction_check(interaction)

    @discord_button(label="Yes", style=ButtonStyle.green)
    async def confirm(self, button: Button, interaction: Interaction):
        self.success = True
        self.stop()

    @discord_button(label="No", style=ButtonStyle.red)
    async def cancel(self, button: Button, interaction: Interaction):
        self.success = False
        self.stop()

    async def request_confirmation(
        self,
        prompt_text=None,
        prompt_embeds: list[discord.Embed] = None,
        ephemeral=False,
        edit=False,
    ):
        """
        Sends a confirmation prompt.

        :param prompt_text: The text the prompt should contain. Optional; defaults to None.
        :param prompt_embeds: A list of embeds the prompt should contain. Optional; defaults to None.
        :param ephemeral: Whether the prompt should be sent as an ephemeral message. Optional; defaults to False.
        :param edit: Whether the prompt should edit an existing interaction response or create a new one.
        Optional; defaults to False.
        """
        if edit:
            await self.ctx.interaction.edit_original_response(
                content=prompt_text, embeds=prompt_embeds, view=self
            )
        else:
            await self.ctx.respond(
                content=prompt_text,
                embeds=prompt_embeds,
                view=self,
                ephemeral=ephemeral,
            )
        await self.wait()
        return self.success


class GameChallengeResponseView(ConfirmationView):
    """
    Provides a user interface for accepting or rejecting a game challenge. This is a subclass of ``ConfirmationView``.
    """

    def __init__(self, challenger: discord.User, game_name: str, **kwargs):
        """
        The constructor for ``GameChallengeResponseView``.

        :param challenger: The user issuing the challenge.
        :param game_name: The name of the game the challenge is for.
        """
        super(GameChallengeResponseView, self).__init__(**kwargs)
        self.challenger = challenger

        self.game_name = game_name
        self.prompt_msg = None
        self.timeout = 90

    async def on_timeout(self) -> None:
        self.clear_items()
        timeout_embed = discord.Embed(
            title="Timeout Error",
            description=f"{self.challenger.mention}'s challenge has been rescinded because "
            f"{self.target_user.mention} took too long to respond.",
            color=discord.Color.red(),
        )
        await self.prompt_msg.edit(content=None, embed=timeout_embed, view=self)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if self.target_user != interaction.user and self.target_user is not None:
            await interaction.response.send_message(
                "You can't respond to a challenge that wasn't addressed to you.",
                ephemeral=True,
            )
        else:
            return await super().interaction_check(interaction)

    async def request_response(self):
        prompt_text = (
            f"Hey {self.target_user.mention}! {self.challenger.mention} is challenging you to "
            f"a game of {self.game_name}! Do you accept?"
        )
        self.prompt_msg = await self.ctx.send(prompt_text, view=self)
        await self.wait()

        if self.success is not None:
            if self.success:
                await self.prompt_msg.edit(
                    content=f"{self.target_user.mention} accepted the challenge!",
                    view=None,
                    delete_after=7,
                )
            else:
                await self.prompt_msg.edit(
                    content=f"{self.target_user.mention} rejected the challenge.",
                    view=None,
                    delete_after=7,
                )

        return self.success


# note: currently unused
class UserSelectionView(EnhancedView):
    """
    Provides an interface for selecting users from a dropdown menu.
    """

    def __init__(self, **kwargs):
        super().__init__()
        self.timeout = None
        self.users = []

    @discord.ui.user_select(placeholder="Select a user", max_values=25)
    async def user_select(self, select: discord.ui.Select, interaction: Interaction):
        self.users = select.values

        if self.users:
            self.stop()

    async def present(
        self,
        prompt_text=None,
        prompt_embeds: list[discord.Embed] = None,
        ephemeral=False,
        edit=False,
    ):
        """
        Sends a user selection prompt.

        Parameters
        ----------
        prompt_text : str, optional, default: None
            The text the prompt should contain.
        prompt_embeds : list[discord.Embed], optional, default: None
            A list of embeds the prompt should contain.
        ephemeral : bool, optional, default: False
            Whether the prompt should be sent as an ephemeral message.
        edit : bool, optional, default: False
            Whether the prompt should edit an existing interaction response or create a new one.
        """
        if edit:
            await self.ctx.interaction.edit_original_response(
                content=prompt_text, embeds=prompt_embeds, view=self
            )
        else:
            await self.ctx.respond(
                content=prompt_text,
                embeds=prompt_embeds,
                view=self,
                ephemeral=ephemeral,
            )
        await self.wait()
        return self.users


class GameThreadURLView(EnhancedView):
    """
    Provides a URL button that points to a newly-created game thread.
    """

    def __init__(self, thread: discord.Thread, **kwargs):
        super().__init__(**kwargs)
        self.add_item(Button(label="Go to game thread", url=thread.jump_url))
