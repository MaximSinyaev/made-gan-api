import os
from celery import Celery
from celery.signals import after_task_publish


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


@after_task_publish.connect
def update_sent_state(sender=None, headers=None, **kwargs):
    task = celery_app.tasks.get(sender)
    backend = task.backend if task else celery_app.backend
    backend.store_result(headers["id"], None, "SENT")
