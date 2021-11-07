import time
from typing import Tuple
from .celery_app import celery_app
from celery import current_task


IMAGE_NAME = "image.png"


@celery_app.task(acks_late=True)
def generate(text: str) -> Tuple[str, str]:
    for i in range(1, 11):
        time.sleep(2)
        current_task.update_state(
            state='PROGRESS',
            meta={'process_percent': i * 10}
        )
    return IMAGE_NAME
