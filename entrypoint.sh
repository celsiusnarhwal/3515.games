#!/usr/bin/env sh

if [ "$ENTRYPOINT" == "api" ]; then
  doppler run -- uvicorn api:app
else
  doppler run -- poetry run python3 main.py
fi