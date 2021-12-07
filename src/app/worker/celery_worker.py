from .celery_app import celery_app
from ..image_generation.image_generator import ImageGeneratorGAN

gan = ImageGeneratorGAN(device='cuda:0')


@celery_app.task(acks_late=True)
def generate_image(text: str):
    return gan.generate_picture(text, width=256, height=256)
