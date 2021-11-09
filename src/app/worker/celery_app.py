import os
from celery import Celery

celery_app = Celery(
    __name__,
    broker=os.environ["CELERY_BROKER_URL"],
    broker_api=os.environ["CELERY_BROKER_API_URL"],
    backend=os.environ["CELERY_BACKEND_URL"],
)
celery_app.conf.task_routes = {
    os.environ["CELERY_GENERATE_IMAGE_TASK_NAME"]: os.environ["CELERY_QUEUE_NAME"]
}
celery_app.conf.update(task_track_started=True, result_extended=True)
