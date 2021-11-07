from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
import logging
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from celery.result import AsyncResult
from worker.celery_worker import generate
from worker.celery_app import celery_app

CFG_PATH = "configs/cfg.yaml"

app = FastAPI()

app.mount("/static", StaticFiles(directory="/static"), name="static")

templates = Jinja2Templates(directory="templates")

log = logging.getLogger(__name__)


class ModelResponse(BaseModel):
    image: str


def celery_on_message(body):
    log.warning(body)


def background_on_message(task):
    log.warning(task.get(on_message=celery_on_message, propagate=False))


@app.get("/")
async def app_root():
    return "Hi!"


@app.get("/generate/{word}")
async def generate(word: str, background_task: BackgroundTasks):
    task_name = None

    # set correct task name based on the way you run the example

    task_name = "app.app.worker.celery_worker.generate"

    task = celery_app.send_task(task_name, args=[word])
    background_task.add_task(background_on_message, task)

    return {"message": f"{task.id} received"}


@app.get("/tasks/{task_uid}")
async def get_result(request: Request, task_uid: str):
    res = AsyncResult(task_uid)
    if res.ready():
        return templates.TemplateResponse("page.html", {"request": request, "text": "картинка", "generated_image": res.result})
    return "ne gotovo"



