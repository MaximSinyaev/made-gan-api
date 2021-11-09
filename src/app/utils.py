from celery.utils.log import get_task_logger
from celery import Task
from typing import NoReturn
from celery import Celery
from celery.app.control import Inspect
import datetime as dt
import pytz


logger = get_task_logger(__name__)


def celery_on_message(body: str) -> NoReturn:
    logger.warning(body)


def background_on_message(task: Task) -> NoReturn:
    logger.warning(task.get(on_message=celery_on_message, propagate=False))


def utc_to_local(utc_dt, timezone="Europe/Moscow"):
    local_tz = pytz.timezone(timezone)
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)


def celery_inspect(celery_app: Celery, task_id: str):
    inspect = Inspect(app=celery_app)
    task_properties = list(inspect.query_task(task_id).values())[0][task_id]
    status, task_info, *_ = task_properties
    text = task_info["args"][0]
    current_time = dt.datetime.now()
    if not task_info["time_start"]:
        start_time = current_time
    else:
        start_time = dt.datetime.fromtimestamp(task_info["time_start"])
    wasted_seconds = (current_time - start_time).seconds
    return text, utc_to_local(start_time), utc_to_local(current_time), wasted_seconds
