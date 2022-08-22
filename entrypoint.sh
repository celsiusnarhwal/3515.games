#!/usr/bin/env bash

if [ "$ENTRYPOINT" == "api" ]; then
  doppler run -- uvicorn api:app --port "$PORT"
else
  doppler run -- poetry run python3 main.py
fi