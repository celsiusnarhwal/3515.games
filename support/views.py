import discord
from discord import Interaction, ButtonStyle
from discord.ui import Button, button as discord_button


class EnhancedView(discord.ui.View):
    """
    A custom ``View`` class that extends Pycord's ``discord.ui.View`` class and that all of 3515.games' views inherit
    from. In addition to everything provided by ``discord.ui.View``, ``EnhancedView`` provides several useful built-in
    instance attributes which are elaborated on in the documentation for its constructor.
    """

    def __init__(self, ctx=None, target_user: discord.User = None):
        """
        The constructor for ``EnhancedView``.

        :param ctx: An ApplicationContext object. Useful to pass in if the view should perform actions in a given
            context. Optional; defaults to None.

        :param target_user: A discord.User object. Useful to pass in if the view should restrict interactions to a
            particular user. Optional; defaults to None.
        """
        super(EnhancedView, self).__init__()
        self.ctx = ctx
        self.target_user = target_user
        self.success = None  # views can use this to indicate their successful completion (vs. timing out)


class ConfirmationView(EnhancedView):
    """
    Provides a user interface for a user to confirm or cancel an action.
    """

    def __init__(self, ctx, **kwargs):
        super(ConfirmationView, self).__init__(ctx, **kwargs)
        self.timeout = 90

    async def on_timeout(self) -> None:
        self.clear_items()
        timeout_embed = discord.Embed(title="Timeout Error", description="You took too long to respond.",
                                      color=discord.Color.red())
        await self.ctx.edit(content=None, embed=timeout_embed, view=self)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if self.target_user != interaction.user and self.target_user is not None:
            await interaction.response.send_message("You can't do that.", ephemeral=True)
        else:
            return await super().interaction_check(interaction)

    @discord_button(label="Yes", style=ButtonStyle.green)
    async def confirm(self, button: Button, interaction: Interaction):
        self.success = True
        self.stop()

    @discord_button(label="No", style=ButtonStyle.red)
    async def cancel(self, button: Button, interaction: Interaction):
        self.success = False
        self.stop()

    async def request_confirmation(self, prompt_text=None, prompt_embeds: list[discord.Embed] = None, ephemeral=False):
        """
        Sends a confirmation prompt in chat.

        :param prompt_text: The text the prompt should contain. Optional; defaults to None.
        :param prompt_embeds: A list of embeds the prompt should contain. Optional; defaults to None.
        :param ephemeral: Whether the prompt should be sent as an ephemeral message. Optional; defaults to False.
        """
        confirmation_prompt: discord.Interaction = await self.ctx.respond(content=prompt_text, embeds=prompt_embeds,
                                                                          view=self,
                                                                          ephemeral=ephemeral)
        await self.wait()
        return {"success": self.success, "prompt": confirmation_prompt}


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

    async def on_timeout(self) -> None:
        self.clear_items()
        timeout_embed = discord.Embed(title="Timeout Error",
                                      description=f"{self.challenger.mention}'s challenge has been rescinded because "
                                                  f"{self.target_user.mention} took too long to respond.",
                                      color=discord.Color.red())
        await self.prompt_msg.edit(content=None, embed=timeout_embed, view=self)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if self.target_user != interaction.user and self.target_user is not None:
            await interaction.response.send_message(
                "You can't respond to a challenge that wasn't addressed to you.", ephemeral=True)
        else:
            return await super().interaction_check(interaction)

    async def request_response(self):
        prompt_text = f"Hey {self.target_user.mention}! {self.challenger.mention} is challenging you to " \
                      f"{self.game_name}! Do you accept?"
        self.prompt_msg = await self.ctx.send(prompt_text, view=self)
        await self.wait()

        if self.success is not None:
            if self.success:
                await self.prompt_msg.edit(f"{self.target_user.mention} accepted the challenge!", view=None,
                                           delete_after=7)
            else:
                await self.prompt_msg.edit(f"{self.target_user.mention} rejected the challenge.", view=None,
                                           delete_after=7)

        return self.success
