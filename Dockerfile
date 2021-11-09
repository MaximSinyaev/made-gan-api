FROM python:3.7-slim

COPY pyproject.toml poetry.lock ./
COPY static/ /static/
COPY templates/ /templates/

ENV CELERY_GENERATE_IMAGE_TASK_NAME=gan_api.src.app.worker.celery_worker.generate_image
ENV STATIC_DIRECTORY=/static
ENV TEMPLATES_DIRECTORY=/templates
ENV CELERY_BROKER_URL=amqp://user:bitnami@rabbitmq:5672//
ENV CELERY_BACKEND_URL=redis://:password123@redis:6379/0
ENV CELERY_QUEUE_NAME=gan-queue

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry && \
    poetry install

EXPOSE 8000