import os
from fastapi import FastAPI, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from celery.result import AsyncResult
from starlette.responses import RedirectResponse
from PIL import Image
from src.app.image_generation.image_generator import LOG
from src.app.translation.text_translator import TextTranslator

from worker.celery_app import celery_app
from sql.session import PostgreSQLSession

OFFSET = 12

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

translator = TextTranslator()

@app.api_route("/generate_image", methods=["GET", "POST"])
async def generate_image(request: Request):
    text = ""
    if request.method == "POST":
        form = await request.form()
        text = translator.translate_to_en(form["text"])
        width = form['width']
        height = form['height']
        text_hash = hash(text)
        task = celery_app.send_task(
            os.environ["CELERY_GENERATE_IMAGE_TASK_NAME"], args=[text, text_hash, width, height]
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
        LOG.info(f'Task already done image path is: {image_path}')
        image_path = image_path.replace('/app/', '../')
        return templates.TemplateResponse(
            os.environ["STATIC_TEMPLATES_RESULT_PAGE"],
            {"request": request, "generated_image": image_path},
        )

    res = AsyncResult(task_id)
    if res.status == "PENDING":
        return Response(status_code=404)
    generated_image = res.result if res.ready() else "gen.gif"
    image_path = os.path.join(os.environ["STATIC_DIRECTORY"], 'images', 'results', f'{task_id}.png')
    if isinstance(generated_image, Image.Image):
        generated_image.save(image_path)
        generated_image = f'results/{task_id}.png'
    if os.path.exists(image_path):
        LOG.info(f'Task already done image path is: {image_path}')
        image_path = image_path.replace('/app/', '../')
        return templates.TemplateResponse(
            os.environ["STATIC_TEMPLATES_RESULT_PAGE"],
            {"request": request, "generated_image": image_path},
        )
    queue_position = int(pg.get_queue_position(task_id)) - OFFSET
    time_delay = 2 * queue_position

    # status = f"Генерация изображения. Примерное время ожидания: {2 * queue_position} минут."

    return templates.TemplateResponse(
        os.environ["DYNAMIC_TEMPLATES_RESULT_PAGE"],
        {"request": request, "status": res.status, "generated_image": generated_image, "time_delay": time_delay},
    )


# functions for bot
def read_image(img_path):
    with open(img_path, "rb") as fin:
        image = fin.read()
    return image


@app.api_route("/generate_image_tg", methods=["GET", "POST"])
async def generate_image_tg(request: Request):
    if request.method == "POST":
        body = await request.body()
        text = translator.translate_to_en(body.decode('utf-8'))
        text_hash = hash(text)
        task = celery_app.send_task(
            os.environ["CELERY_GENERATE_IMAGE_TASK_NAME"], args=[text, text_hash]
        )
        queue_position = int(pg.get_queue_position(task.id)) - OFFSET
        response = Response(content=",".join([task.id, str(queue_position)]), status_code=200)
        return response
    else:
        return Response(status_code=404)


@app.api_route("/tasks/tg", methods=["GET", "POST"])
async def get_result_tg(request: Request):
    if request.method == "POST":
        body = await request.body()
        task_id = body.decode()
        res = AsyncResult(task_id)
        if not res.ready():
            queue_position = str(pg.get_queue_position(task_id))
            return Response(content=queue_position, status_code=409)
        elif res.ready():
            generated_image = res.result
            image_path = os.path.join(os.environ["STATIC_DIRECTORY"], 'images', 'results', f'{task_id}.png')
            generated_image.save(image_path)
            image_binary = read_image(image_path)
            return Response(content=image_binary, status_code=200)
        else:
            return Response(status_code=404)
    else:
        return Response(status_code=404)


@app.api_route("/tasks/tg_queue", methods=["GET", "POST"])
async def get_result_tg(request: Request):
    if request.method == "POST":
        body = await request.body()
        task_id = body.decode()
        res = AsyncResult(task_id)
        if not res.ready():
            queue_position = str(int(pg.get_queue_position(task_id)) - OFFSET)
            return Response(content=queue_position, status_code=200)
        else:
            return Response(status_code=404)
    else:
        return Response(status_code=404)