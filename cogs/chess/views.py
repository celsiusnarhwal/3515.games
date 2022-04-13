from __future__ import annotations

from discord.ui import Button

from support import EnhancedView


class GoToChessThreadView(EnhancedView):
    """
    Provides a URL button that points to a newly-created Chess game thread.
    """

    def __init__(self, thread_url, **kwargs):
        super().__init__(**kwargs)
        self.add_item(Button(label="Go to game thread", url=thread_url))
