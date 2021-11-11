FROM nvidia/cuda:11.1-base-ubuntu18.04 as run-image



ENV CELERY_GENERATE_IMAGE_TASK_NAME=gan_api.src.app.worker.celery_worker.generate_image
ENV STATIC_DIRECTORY=/static
ENV TEMPLATES_DIRECTORY=/templates
ENV TEMPLATES_GENERATE_IMAGE_PAGE=generate_image.html
ENV TEMPLATES_RESULT_PAGE=result.html
ENV CELERY_BROKER_URL=amqp://user:bitnami@rabbitmq:5672//
ENV CELERY_BROKER_API_URL=http://user:bitnami@rabbitmq:15672/api/
ENV CELERY_BACKEND_URL=db+postgresql://postgres:password123@postgresql/gan_api
ENV CELERY_QUEUE_NAME=gan-queue

# Install some basic utilities
RUN apt-get update && apt-get install -y \
    git \
    bzip2 \
    libx11-6 \
    curl \
 && rm -rf /var/lib/apt/lists/*


# Create a working directory
RUN mkdir /app
WORKDIR /app

RUN mkdir models
RUN curl -L -o models/vqgan_imagenet_f16_16384.yaml -C - 'https://heibox.uni-heidelberg.de/d/a7530b09fed84f80a887/files/?p=%2Fconfigs%2Fmodel.yaml&dl=1' #ImageNet 16384
RUN curl -L -o models/vqgan_imagenet_f16_16384.ckpt -C - 'https://heibox.uni-heidelberg.de/d/a7530b09fed84f80a887/files/?p=%2Fckpts%2Flast.ckpt&dl=1' #ImageNet 16384


COPY pyproject.toml poetry.lock ./
COPY static/ /static/
COPY templates/ /templates/

# Create a non-root user and switch to it
RUN adduser --disabled-password --gecos '' --shell /bin/bash user \
 && chown -R user:user /app
RUN echo "user ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-user
USER user

# All users can use /home/user as their home directory
ENV HOME=/home/user
RUN chmod 777 /home/user

# Install Miniconda and Python 3.8
ENV CONDA_AUTO_UPDATE_CONDA=false
ENV PATH=/home/user/miniconda/bin:$PATH
RUN curl -sLo ~/miniconda.sh https://repo.continuum.io/miniconda/Miniconda3-py38_4.8.2-Linux-x86_64.sh \
 && chmod +x ~/miniconda.sh \
 && ~/miniconda.sh -b -p ~/miniconda \
 && rm ~/miniconda.sh \
 && conda install -y python==3.8.1 \
 && conda clean -ya

 RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry && \
    poetry install

# # CUDA 10.2-specific steps
RUN conda install -y -c pytorch -c conda-forge\
     pytorch==1.8.0 cudatoolkit=11.1


COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

ENV PYTHONPATH=${PYTHONPATH}:/app

COPY ./src /app/src


EXPOSE 8000
