import os
import time

import aiohttp
import time

import asyncio

from storage_utils import ImagesDB

API_URL = os.getenv("FASTAPI_HOST")
AWAIT_TIME = 5
TIME_LIMIT = 60 * 30
FREQUENCY = 10

db = ImagesDB()


async def send_text(text):
    data = text
    task_id = None
    queue_position = None
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL + "/generate_image_tg",
                                data=data.encode('utf-8'),
                                headers={'Content-type': 'text/plain; charset=utf-8'}
                                ) as response:
            if response.status == 200:
                # task_id, queue_position = await response.text().split(",")
                text = await response.text()
                task_id, queue_position = text.split(",")
    return task_id, queue_position


async def get_image(task_id):
    data = task_id
    image = None
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL + f"/tasks/tg", data=data) as response:
            if response.status == 200:
                image = await response.content.read()
            elif response.status == 409:
                # queue_position = await response.text().split(",")
                text = await response.text()
                queue_position = text
                await db.update_image_queue_position(task_id, queue_position)
                await asyncio.sleep(AWAIT_TIME)
    return image


async def get_image_loop(task_id, freq=FREQUENCY, time_limit=TIME_LIMIT):
    time_start = time.time()
    image = None
    while time.time() - time_start < time_limit:
        image = await get_image(task_id)
        if image is not None:
            break
        else:
            await asyncio.sleep(freq)
    return image
