import os
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from celery.result import AsyncResult
from starlette.responses import RedirectResponse

from worker.celery_app import celery_app
from utils import background_on_message, celery_inspect

templates = Jinja2Templates(directory=os.environ["TEMPLATES_DIRECTORY"])

app = FastAPI()
app.mount(
    os.environ["STATIC_DIRECTORY"],
    StaticFiles(directory=os.environ["STATIC_DIRECTORY"]),
)


@app.api_route("/generate_image", methods=["GET", "POST"])
async def generate_image(request: Request, background_task: BackgroundTasks):
    text = ""
    if request.method == "POST":
        form = await request.form()
        text = form["text"]
        task = celery_app.send_task(
            os.environ["CELERY_GENERATE_IMAGE_TASK_NAME"], args=[text]
        )
        background_task.add_task(background_on_message, task)
        response = RedirectResponse(url=f"/tasks/{task.id}")
        response.status_code = 302
        return response
    return templates.TemplateResponse(
        "generate_image.html", {"request": request, "text": text}
    )


@app.get("/tasks/{task_id}")
async def get_result(request: Request, task_id: str):
    res = AsyncResult(task_id)
    if res.ready():
        return templates.TemplateResponse(
            "page.html", {"request": request, "generated_image": res.result},
        )
    try:
        text, start_time, current_time, wasted_seconds = celery_inspect(celery_app, task_id)
        start_time = start_time.strftime("%H:%M:%S")
        current_time = current_time.strftime("%H:%M:%S")
        return (
            f"Статус: {res.status}, Текст: {text}, Время старта: {start_time}, "
            f"Текущее время: {current_time}, Потрачено секунд: {wasted_seconds}"
        )
    except KeyError:
        return "Обновите страницу позднее"

