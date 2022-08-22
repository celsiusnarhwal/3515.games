#!/usr/bin/env bash

if [ "$ENTRYPOINT" == "api" ]; then
  doppler run -- uvicorn api:app --host "0.0.0.0" --port "$PORT"
else
  doppler run -- poetry run python3 main.py
fi