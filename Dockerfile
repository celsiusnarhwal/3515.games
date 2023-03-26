FROM python:3.11.1

ENV POETRY_VERSION=1.4.1
ENV POETRY_HOME=/opt/poetry
ENV PATH="${PATH}:${POETRY_HOME}/bin"

COPY . /app

WORKDIR /app/bot

RUN curl -sSL https://install.python-poetry.org | python - && poetry install --no-root --only main

ENTRYPOINT ["poetry", "run", "python", "main.py"]