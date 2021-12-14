FROM nvidia/cuda:11.1-base-ubuntu18.04 as run-image

# Install some basic utilities
RUN apt-get update && apt-get install -y \
    git \
    bzip2 \
    libx11-6 \
    curl \
    python3.8 \
    python3-pip \
 && rm -rf /var/lib/apt/lists/*

# Create a working directory
RUN mkdir /app
WORKDIR /app

RUN mkdir models
RUN curl -L -o models/vqgan_imagenet_f16_16384.yaml -C - 'https://heibox.uni-heidelberg.de/d/a7530b09fed84f80a887/files/?p=%2Fconfigs%2Fmodel.yaml&dl=1' #ImageNet 16384
RUN curl -L -o models/vqgan_imagenet_f16_16384.ckpt -C - 'https://heibox.uni-heidelberg.de/d/a7530b09fed84f80a887/files/?p=%2Fckpts%2Flast.ckpt&dl=1' #ImageNet 16384


COPY pyproject.toml poetry.lock ./

# Create a non-root user and switch to it
RUN adduser --disabled-password --gecos '' --shell /bin/bash user \
 && chown -R user:user /app
# RUN echo "user ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-user
RUN chmod 777 /app
USER user

# All users can use /home/user as their home directory
ENV HOME=/home/user
RUN chmod 777 /home/user

RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir poetry

ENV PATH "$PATH:/home/user/.local/bin"
ENV PYTHONIOENCODING=utf-8

RUN poetry install && \
    pip3 install poethepoet && \
    poe force-cuda-task

RUN pip install --no-cache-dir requests pyTelegramBotAPI

ENV PYTHONPATH=${PYTHONPATH}:/app
ENV CELERY_GENERATE_IMAGE_TASK_NAME=src.app.worker.celery_worker.generate_image
ENV STATIC_DIRECTORY=/app/static
ENV TEMPLATES_DIRECTORY=/app/templates
ENV TEMPLATES_GENERATE_IMAGE_PAGE=generate_image.html
ENV DYNAMIC_TEMPLATES_RESULT_PAGE=dynamic_result.html
ENV STATIC_TEMPLATES_RESULT_PAGE=static_result.html
ENV CELERY_BROKER_URL=amqp://user:bitnami@rabbitmq:5672//
ENV CELERY_BROKER_API_URL=http://user:bitnami@rabbitmq:15672/api/
ENV CELERY_BACKEND_URL=db+postgresql://postgres:password123@postgresql/gan_api
ENV CELERY_QUEUE_NAME=gan-queue
ENV PG_CONNECTION_STRING="postgresql://postgres:password123@postgresql:5432/gan_api?gssencmode=disable"


RUN mkdir /app/gan_api
COPY ./src /app/src
# COPY static/ /app/static
# COPY templates/ /app/templates

EXPOSE 8000