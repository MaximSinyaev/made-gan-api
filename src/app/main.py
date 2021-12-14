import os
from fastapi import FastAPI, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from celery.result import AsyncResult
from starlette.responses import RedirectResponse
from PIL import Image
from src.app.image_generation.image_generator import LOG

from worker.celery_app import celery_app
from sql.session import PostgreSQLSession

pg = PostgreSQLSession(os.environ["PG_CONNECTION_STRING"])

templates = Jinja2Templates(directory=os.environ["TEMPLATES_DIRECTORY"])

app = FastAPI()
app.mount(
    "/static",
    StaticFiles(directory=os.environ["STATIC_DIRECTORY"]),
)

result_directory = os.path.join(os.environ["STATIC_DIRECTORY"], 'images', 'results')
if not os.path.exists(result_directory):
    os.makedirs(result_directory)


@app.api_route("/generate_image", methods=["GET", "POST"])
async def generate_image(request: Request):
    text = ""
    if request.method == "POST":
        form = await request.form()
        LOG.info(f"{form}")
        text = form["text"]
        text_hash = hash(text)
        task = celery_app.send_task(
            os.environ["CELERY_GENERATE_IMAGE_TASK_NAME"], args=[text, text_hash]
        )
        response = RedirectResponse(url=f"/tasks/{task.id}", status_code=302)
        return response
    return templates.TemplateResponse(
        os.environ["TEMPLATES_GENERATE_IMAGE_PAGE"], {"request": request, "text": text}
    )


@app.get("/tasks/{task_id}")
async def get_result(request: Request, task_id: str):
    image_path = os.path.join(os.environ["STATIC_DIRECTORY"], 'images', 'results', f'{task_id}.png')
    if os.path.exists(image_path):
        return templates.TemplateResponse(
            os.environ["STATIC_TEMPLATES_RESULT_PAGE"],
            {"request": request, "generated_image": image_path},
        )

    res = AsyncResult(task_id)
    if res.status == "PENDING":
        return Response(status_code=404)
    generated_image = res.result if res.ready() else "gen.gif"
    # LOG.info(f'generated image: {generated_image}, task result {res.result}, task state: {res.ready()}')
    if isinstance(generated_image, Image.Image):
        generated_image.save(image_path)
        generated_image = f'results/{task_id}.png'
        # LOG.info(f'New image: {generated_image}')
        # LOG.info(f'{os.listdir(os.path.join(os.environ["STATIC_DIRECTORY"], "results"))}')
    status = res.status
    if not res.ready():
        queue_position = pg.get_queue_position(task_id)
        status += f" (Ваше место в очереди: {queue_position})"
    return templates.TemplateResponse(
        os.environ["DYNAMIC_TEMPLATES_RESULT_PAGE"],
        {"request": request, "status": res.status, "generated_image": generated_image},
    )
