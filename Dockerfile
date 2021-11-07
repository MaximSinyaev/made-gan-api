FROM python:3.7-slim

LABEL maintainer="Grega Vrbančič <grega.vrbancic@gmail.com"

ENV DOCKER=true

COPY pyproject.toml poetry.lock ./
COPY static/ /static/
COPY templates/ /templates/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry && \
    poetry install

EXPOSE 8000