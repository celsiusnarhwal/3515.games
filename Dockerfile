FROM python:3.11.1

ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PIP_ROOT_USER_ACTION=ignore
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PATH="${PATH}:${POETRY_HOME}/bin"

COPY . /app

WORKDIR /app

RUN curl -sSL https://cli.doppler.com/install.sh | sh && \
    curl -sSL https://install.python-poetry.org | python - --version $(cat .poetry-version) && \
    poetry install --only main && \
    spacy download en_core_web_sm

WORKDIR /app/bot

CMD ["doppler", "run", "--", "python", "main.py"]