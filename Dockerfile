FROM python:3.11.1

ENV POETRY_HOME=/opt/poetry
ENV PATH="${PATH}:${POETRY_HOME}/bin:/root/.local/bin"

COPY . /app

WORKDIR /app

RUN curl -sSL https://cli.doppler.com/install.sh | sh && \
    curl -sSL https://install.python-poetry.org | python - --version $(python poet.py) && \
    poetry install --only main

CMD ["doppler", "run", "--", "poetry", "run", "python", "main.py"]