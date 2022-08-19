FROM python:3.10.2

ENV POETRY_VERSION=1.1.13
ENV PATH="${PATH}:/root/.local/bin"

COPY . .

# Install Doppler CLI
RUN apt-get update && apt-get install -y apt-transport-https ca-certificates curl gnupg && \
    curl -sLf --retry 3 --tlsv1.2 --proto "=https" 'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key' | apt-key add - && \
    echo "deb https://packages.doppler.com/public/cli/deb/debian any-version main" | tee /etc/apt/sources.list.d/doppler-cli.list && \
    apt-get update && \
    apt-get -y install doppler

# Install Poetry and Dependencies
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    poetry config virtualenvs.create false &&  \
    poetry install --no-dev

# Start it up!
ENTRYPOINT ["doppler", "run", "--", "poetry", "run", "python3", "main.py"]