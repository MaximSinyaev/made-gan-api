import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from celery.result import AsyncResult
from starlette.responses import RedirectResponse

from worker.celery_app import celery_app

templates = Jinja2Templates(directory=os.environ["TEMPLATES_DIRECTORY"])

app = FastAPI()
app.mount(
    os.environ["STATIC_DIRECTORY"],
    StaticFiles(directory=os.environ["STATIC_DIRECTORY"]),
)


@app.api_route("/generate_image", methods=["GET", "POST"])
async def generate_image(request: Request):
    text = ""
    if request.method == "POST":
        form = await request.form()
        text = form["text"]
        task = celery_app.send_task(
            os.environ["CELERY_GENERATE_IMAGE_TASK_NAME"], args=[text]
        )
        response = RedirectResponse(url=f"/tasks/{task.id}")
        response.status_code = 302
        return response
    return templates.TemplateResponse(
        "generate_image.html", {"request": request, "text": text}
    )


@app.get("/tasks/{task_id}")
async def get_result(request: Request, task_id: str):
    res = AsyncResult(task_id)
    generated_image = res.result if res.ready() else "gen.gif"
    return templates.TemplateResponse(
        "page.html",
        {"request": request, "status": res.status, "generated_image": generated_image},
    )