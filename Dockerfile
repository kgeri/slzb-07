FROM python:3-slim AS build-env

WORKDIR /app
COPY requirements.txt /app
RUN pip install -Ur requirements.txt
COPY config.toml zigbee.db* *.py /app

CMD ["python3", "zigbee-listener.py"]
