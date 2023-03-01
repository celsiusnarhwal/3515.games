FROM python:3.11.1

ENV POETRY_VERSION=1.3.2
ENV POETRY_HOME=/opt/poetry
ENV PATH="${PATH}:${POETRY_HOME}/bin"

COPY COPYING pyproject.toml poetry.lock /bot/
COPY src /bot/src

WORKDIR /bot

RUN curl -sSL https://install.python-poetry.org | python - && poetry install --no-root --only main

ENTRYPOINT ["poetry", "run", "python", "src/main.py"]