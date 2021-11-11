FROM python:3.7-slim

COPY pyproject.toml poetry.lock ./
COPY static/ /static/
COPY templates/ /templates/

ENV CELERY_GENERATE_IMAGE_TASK_NAME=gan_api.src.app.worker.celery_worker.generate_image
ENV STATIC_DIRECTORY=/static
ENV TEMPLATES_DIRECTORY=/templates
ENV TEMPLATES_GENERATE_IMAGE_PAGE=generate_image.html
ENV TEMPLATES_RESULT_PAGE=result.html
ENV CELERY_BROKER_URL=amqp://user:bitnami@rabbitmq:5672//
ENV CELERY_BROKER_API_URL=http://user:bitnami@rabbitmq:15672/api/
ENV CELERY_BACKEND_URL=db+postgresql://postgres:password123@postgresql/gan_api
ENV CELERY_QUEUE_NAME=gan-queue

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry &&  \
    poetry install && \
    pip install poethepoet &&  \
    poe force-cuda-task

EXPOSE 8000