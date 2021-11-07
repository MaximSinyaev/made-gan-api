from celery import Celery

celery_app = Celery(
    __name__,
    broker="amqp://user:bitnami@rabbitmq:5672//",
    backend="redis://:password123@redis:6379/0"
)
celery_app.conf.task_routes = {
    "app.app.worker.celery_worker.generate": "test-queue"
}
celery_app.conf.update(task_track_started=True)
