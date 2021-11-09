import os
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from celery.result import AsyncResult
from starlette.responses import RedirectResponse

from worker.celery_app import celery_app
from utils import background_on_message

templates = Jinja2Templates(directory=os.environ["TEMPLATES_DIRECTORY"])

app = FastAPI()
app.mount(
    os.environ["STATIC_DIRECTORY"],
    StaticFiles(directory=os.environ["STATIC_DIRECTORY"]),
)


@app.get("/")
async def app_root():
    return "Hi!"


@app.get("/generate_image/{text}")
async def generate_image(text: str, background_task: BackgroundTasks):
    task = celery_app.send_task(
        os.environ["CELERY_GENERATE_IMAGE_TASK_NAME"], args=[text]
    )
    background_task.add_task(background_on_message, task)
    return RedirectResponse(url=f"/tasks/{task.id}")


@app.get("/tasks/{task_id}")
async def get_result(request: Request, task_id: str):
    res = AsyncResult(task_id)
    if res.ready():
        return templates.TemplateResponse(
            "page.html",
            {"request": request, "text": "картинка", "generated_image": res.result},
        )
    return res.status
