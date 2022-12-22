"""
Development settings.
"""

from settings.base import Settings

settings = Settings(
    bot_name="3515.games.dev",
    app_id=960228863986761778,
    database={
        "provider": "sqlite",
        "filename": "db.sqlite",
        "create_db": True,
    }
)
