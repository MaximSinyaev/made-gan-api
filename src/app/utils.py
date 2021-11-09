from celery.utils.log import get_task_logger
from celery import Task
from typing import NoReturn

logger = get_task_logger(__name__)


def celery_on_message(body: str) -> NoReturn:
    logger.warning(body)


def background_on_message(task: Task) -> NoReturn:
    logger.warning(task.get(on_message=celery_on_message, propagate=False))
