import hashlib
import datetime
import os
import requests
import time

API_URL = os.getenv("FASTAPI_HOST")
N_TRIES = 2
AWAIT_TIME = 5
TIME_LIMIT = 60 * 30
FREQUENCY = 10


def send_text(text, n_tries=N_TRIES, await_time=AWAIT_TIME):
    data = text
    task_id = None
    text = text
    for _ in range(n_tries):
        response = requests.post(
            API_URL + "/generate_image_tg", 
            data=data.encode('utf-8'),
            headers={'Content-type': 'text/plain; charset=utf-8'}
            )
        if response.status_code == 200:
            task_id = response.content
            break
        else:
            time.sleep(await_time)
    print(task_id)
    return task_id.decode()


def get_image(task_id, n_tries=N_TRIES, await_time=AWAIT_TIME):
    data = task_id
    image = None
    for _ in range(n_tries):
        response = requests.post(API_URL + f"/tasks/tg", data=data)
        print(response)
        if response.status_code == 200:
            image = response.content
            break
        else:
            time.sleep(await_time)
    return image


def get_image_loop(task_id, freq=FREQUENCY, time_limit=TIME_LIMIT):
    time_start = time.time()
    image = None
    while time.time() - time_start < time_limit:
        image = get_image(task_id)
        if image is not None:
            break
        else:
            time.sleep(freq)
    return image
