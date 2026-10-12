FROM python:3.13-slim AS build-env

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app
RUN pip install -Ur requirements.txt
COPY config.toml zigbee.db* *.py /app

CMD ["python3", "zigbee-listener.py"]
