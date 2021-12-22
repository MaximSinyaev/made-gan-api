import datetime
import os

import asyncio
from telebot.async_telebot import AsyncTeleBot

from storage_utils import ImagesDB
import service_api

BOT_PATH = os.path.abspath(os.getcwd())
STATIC_PATH = os.getenv("STATIC_PATH")

example_image_directory = os.path.join(STATIC_PATH, 'images')

with open(os.path.join(BOT_PATH, "API_KEY.log"), "rt") as fin:
    API_KEY = fin.read()
    print(API_KEY)


bot = AsyncTeleBot(API_KEY)
# bot = telebot.TeleBot(API_KEY)
db = ImagesDB()
user_state = {}


async def get_user_step(uid):
    if await db.check_user(uid):
        return user_state[uid]
    else:
        await db.add_user(uid, "TODO")
        user_state[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0


# handle the "/start" command
@bot.message_handler(commands=['start'])
async def command_start(message):
    cid = message.chat.id
    name = message.from_user.username
    await db.add_log("user", message.text, cid)
    # greeting_message = "Hello, this is an illustration bot! Glad to see you here!"
    greeting_message = "Привет, это бот для генерации иллюстраций! Рад видеть тебя в этом чате!"
    await db.add_log("bot", greeting_message, cid)
    await bot.send_message(cid, greeting_message)
    greeting_message_extra = "Напиши текст, который хочешь визуализировать," +\
                             " и классная нейронная сеть нарисует для тебя иллюстрацию!" +\
                             "\nТакже можно заказть желаемый стиль, подробности можно узнать по команде /help"
    await db.add_log("bot", greeting_message_extra, cid)
    await bot.send_message(cid, greeting_message_extra)
    if await db.check_user_status(cid) == -1:
        await db.add_user(cid, name)


# help page
@bot.message_handler(commands=['help'])
async def command_help(message):
    cid = message.chat.id
    # help_text = "Write some text and awesome neural network will draw an illustration for you!"
    help_text = "Напиши текст, который хочешь визуализировать," +\
                " и классная нейронная сеть нарисует для тебя иллюстрацию!" +\
                "\nЧтобы добавить желаемый стиль, его можно написать через `|`. " +\
                "Например, вот так: 'горный пейзаж | рисунок карандашом'"
    await db.add_log("bot", help_text, cid)
    await bot.send_message(cid, help_text)  # send the generated help page
    with open(os.path.join("storage/", "Example.jpg"), "rb") as fin:
        image = fin.read()
    await bot.send_photo(cid, image)
    help_text_extra = "Больше примеров доступно по ссылке:\n" + \
                      "https://imgur.com/a/SALxbQm"
    await db.add_log("bot", help_text_extra, cid)
    await bot.send_message(cid, help_text_extra)  # send the generated help page


@bot.message_handler(func=lambda message: True)
async def message_manager(message):
    status = await db.check_user_status(message.chat.id)
    if status == 0:
        await generate_text_handler(message)
        return
    elif status == 1:
        await wait_image_handler(message)
        return
    elif status == -1:
        await no_start_handler(message)
        return
    else:
        await command_default(message)


@bot.message_handler(content_types=['text'])
async def generate_text_handler(message):
    cid = message.chat.id
    await db.add_log("user", message.text, cid)
    task_id, queue_position = await service_api.send_text(message.text)
    flag = False
    if task_id is not None:
        # bot_text = "Please wait, image is generating.\n" +\
        #            f"Your position in queue: {queue_position}"
        bot_text = "Подожди, пожалуйста. Нейронная сеть уже готовит краски, скоро картинка будет готова!\n" + \
                   f"Приблизительное время ожидания в минутах: {int(queue_position) * 2}"
        await bot.send_message(cid, bot_text)
        await db.add_image(cid, message.text, task_id, queue_position)
        await db.add_log("bot", bot_text, cid)
        await db.update_user_status(cid, 1)
        image = await service_api.get_image_loop(task_id)
        if image is None:
            flag = False
        else:
            await bot.send_photo(cid, image)
            await db.add_log("bot", f"send image with task_id: {task_id}", cid)
            flag = True
    if not flag:
        # bot_text = "Something went wrong, please try again later"
        bot_text = "Что-то пошло не так, пожалуйста, попробуй позже."
        await bot.send_message(cid, bot_text)
        await db.add_log("bot", bot_text, cid)
    await db.update_user_status(cid, 0)


@bot.message_handler(content_types=['text'])
async def wait_image_handler(message):
    cid = message.chat.id
    await db.add_log("user", message.text, cid)
    # some api-fal and restart correction
    cur_dt = datetime.datetime.now()
    last_dt = datetime.datetime.fromisoformat(await db.get_time_of_last_task(cid))
    df_diff = cur_dt - last_dt
    # reset status if user waits too long
    if df_diff.seconds > service_api.TIME_LIMIT + service_api.FREQUENCY + service_api.AWAIT_TIME:
        await db.update_user_status(cid, 0)
        await db.add_log("system", "hard reset status", cid)
        await generate_text_handler(message)
        return
    queue_position = await db.check_user_queue_position(cid)
    # bot_text = "Please wait, image is generating. Can generate only one image at time.\n" +\
    #            f"Your position in queue: {queue_position}"
    bot_text = "Пожалуйста, подожди, нейронная сеть старается, но может рисовать только 1 картинку за раз.\n" + \
               f"Приблизительное время ожидания в минутах: {int(queue_position) * 2}"
    await bot.send_message(cid, bot_text)
    await db.add_log("bot", bot_text, cid)


@bot.message_handler(content_types=['text'])
async def no_start_handler(message):
    await command_start(message)


@bot.message_handler(func=lambda message: True)
async def command_default(message):
    # this is the standard reply to a normal message
    cid = message.chat.id
    # bot_text = "I don't understand \"" + message.text + "\"\nMaybe try the help page at `/help`"
    bot_text = "Я не понял \"" + message.text + "\"\nПопробуй команду  /help"
    await bot.send_message(cid, bot_text)
    await db.add_log("bot", bot_text, cid)


def main():
    asyncio.run(bot.infinity_polling())


if __name__ == "__main__":
    main()
