"""
Production settings.
"""
import os

from settings.base import Settings

settings = Settings(
    bot_name="3515.games",
    app_id=939972078323519488,
    database={
        "provider": "postgres",
        "dsn": os.getenv("DATABASE_URL"),
    }
)
