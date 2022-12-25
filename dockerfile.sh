# For use in development only.

docker build . -t 3515.games:latest
docker run --rm --env-file <(doppler secrets download --no-file --format docker) 3515.games:latest
