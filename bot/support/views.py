########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import sys
from abc import ABC, abstractmethod

import discord
import discord.ui
from discord import ButtonStyle, Interaction
from discord.ui import Button, Item
from discord.ui import button as discord_button


class View(discord.ui.View):
    """
    Base class for 3515.games' views.
    """

    def __init__(
        self,
        ctx: discord.ApplicationContext = None,
        target_user: discord.User = None,
        *args,
        **kwargs,
    ):
        """
        The constructor for ``EnhancedView``.

        :param ctx: An ApplicationContext object. Useful to pass in if the view should perform actions in a given
            context. Optional; defaults to None.

        :param target_user: A discord.User object. Useful to pass in if the view should restrict interactions to a
            particular user. Optional; defaults to None.
        """
        super().__init__(*args, **kwargs)
        self.ctx: discord.ApplicationContext = ctx
        self.target_user: discord.User = target_user
        self.timeout = None
        self.success = None  # views can use this to indicate their successful completion (vs. timing out)

    def on_error(self, error: Exception, item: Item, interaction: Interaction) -> None:
        sys.excepthook(type(error), error, error.__traceback__)

    async def full_stop(self):
        """
        Make the view stop listening for interactions and disable all of its components.
        """
        self.stop()
        self.disable_all_items()
        await self.ctx.interaction.edit_original_response(view=self)


class ConfirmationView(View):
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


class UserSelectionView(View, ABC):
    """
    Provides an interface for selecting users from a dropdown menu.
    """

    def __init__(
        self,
        min_users: int = 1,
        max_users: int = 25,
        placeholder: str = "Select a user",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.min_users = min_users
        self.max_users = max_users
        self.placeholder = placeholder

        select = discord.ui.Select(
            select_type=discord.ComponentType.user_select,
            min_values=self.min_users,
            max_values=self.max_users,
            placeholder=self.placeholder,
        )

        select.callback = self.callback

        self.add_item(select)

    async def callback(self, interaction: Interaction):
        pass

    @abstractmethod
    async def present(self, *args, **kwargs):
        ...


class GameThreadURLView(View):
    """
    Provides a URL button that points to a newly-created game thread.
    """

    def __init__(self, thread: discord.Thread, **kwargs):
        super().__init__(**kwargs)
        self.add_item(Button(label="Go to game thread", url=thread.jump_url))


class GameVoiceURLView(View):
    """
    Provides a URL button that points to a game's associated voice channel.
    """

    def __init__(self, channel: discord.VoiceChannel, **kwargs):
        super().__init__(**kwargs)
        self.add_item(Button(label="Join voice channel", url=channel.jump_url))
