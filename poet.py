"""
Maintains a consistent Poetry version in Docker containers and CI systems.
"""

import tomllib

print(tomllib.load(open("pyproject.toml", "rb"))["extra"]["poetry-version"])
