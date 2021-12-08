import torch
from .celery_app import celery_app
from ..image_generation.image_generator import ImageGeneratorGAN

gan = ImageGeneratorGAN(device='cuda' if torch.cuda.is_available() else 'cpu')


@celery_app.task(acks_late=True)
def generate_image(text: str, task_id: str):
    return gan.generate_picture(text, filename=task_id, width=256, height=256)
