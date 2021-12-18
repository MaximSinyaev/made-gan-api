FROM python:3.9-slim as compile-image

COPY requirements.txt /requirements.txt
RUN python -m venv /opt/venv
RUN /opt/venv/bin/pip install --no-cache-dir -r /requirements.txt

FROM python:3.9-slim as run-image

ENV PYTHONPATH=${PYTHONPATH}:/app

RUN adduser docker
USER docker

WORKDIR /app
COPY --from=compile-image /opt/venv /opt/venv
COPY . /app/app
COPY ./API_KEY.log /app/API_KEY.log

ENTRYPOINT ["/opt/venv/bin/python", "app/bot.py"]
