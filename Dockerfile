FROM python:3.10.2

ENV POETRY_VERSION=1.1.13
ENV PATH="${PATH}:/root/.poetry/bin"

COPY . .

RUN curl -sSL https://install.python-poetry.org | python3 -
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

ENTRYPOINT ["poetry", "run", "python3", "main.py"]
