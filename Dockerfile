FROM python:3.10.2

ENV POETRY_VERSION=1.1.13
ENV PATH="${PATH}:/root/.poetry/bin"

COPY . .

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3 -
RUN poetry install --no-dev

ENTRYPOINT ["poetry", "run", "python3", "main.py"]
