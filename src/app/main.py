import os
from fastapi import FastAPI, Request, Response
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


def read_image(img_path):
    with open("../static/images/" + img_path, "rb") as fin:
        image = fin.read()
    return image


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
        os.environ["TEMPLATES_GENERATE_IMAGE_PAGE"], {"request": request, "text": text}
    )


@app.api_route("/generate_image_tg", methods=["GET", "POST"])
async def generate_image_tg(request: Request):
    if request.method == "POST":
        body = await request.body()
        text = body.decode()
        task = celery_app.send_task(
            os.environ["CELERY_GENERATE_IMAGE_TASK_NAME"], args=[text]
        )
        response = Response(content=task.id, status_code=200)
        return response
    else:
        return Response(status_code=404)


@app.get("/tasks/{task_id}")
async def get_result(request: Request, task_id: str):
    res = AsyncResult(task_id)
    if res.status == "PENDING":
        return Response(status_code=404)
    generated_image = res.result if res.ready() else "gen.gif"
    return templates.TemplateResponse(
        os.environ["TEMPLATES_RESULT_PAGE"],
        {"request": request, "status": res.status, "generated_image": generated_image},
    )


@app.api_route("/tasks/tg", methods=["GET", "POST"])
async def get_result_tg(request: Request):
    if request.method == "POST":
        body = await request.body()
        task_id = body.decode()
        res = AsyncResult(task_id)
        if res.status == "PENDING":
            return Response(status_code=404)
        elif res.ready():
            generated_image = read_image(res.result)
            return Response(content=generated_image, status_code=200)
        else:
            return Response(status_code=404)
    else:
        return Response(status_code=404)
