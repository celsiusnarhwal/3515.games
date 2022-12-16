FROM python:3.10.2

ENV POETRY_VERSION=1.1.13
ENV PATH="${PATH}:/root/.local/bin"

COPY . .

# Install dependencies
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    poetry config virtualenvs.create false &&  \
    poetry install --no-dev

# Start it up!
ENTRYPOINT ["poetry", "run", "python3", "main.py"]