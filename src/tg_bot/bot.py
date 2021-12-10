import telebot
import os
from storage_utils import ImagesDB
import service_api

BOT_PATH = "/app/gan_api/src/tg_bot/"

with open(os.path.join(BOT_PATH, "API_KEY.log"), "rt") as fin:
    API_KEY = fin.read()


bot = telebot.TeleBot(API_KEY)
db = ImagesDB()
user_state = {}


def get_user_step(uid):
    if db.check_user(uid):
        return user_state[uid]
    else:
        db.add_user(uid, "TODO")
        user_state[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0


# handle the "/start" command
@bot.message_handler(commands=['start'])
def command_start(message):
    cid = message.chat.id
    name = message.from_user.username
    db.add_log("user", message.text, cid)
    greeting_message = "Hello, this is an illustration bot! Glad to see you here!"
    bot.send_message(cid, greeting_message)
    db.add_log("bot", greeting_message, cid)
    if db.check_user_status(cid) == -1:
        db.add_user(cid, name)
        # db.add_welcome_image(cid)
    command_help(message)


# help page
@bot.message_handler(commands=['help'])
def command_help(message):
    cid = message.chat.id
    help_text = "Write some text and awesome neural network will draw an illustration for you!"
    bot.send_message(cid, help_text)  # send the generated help page
    db.add_log("bot", help_text, cid)


@bot.message_handler(func=lambda m: db.check_user_status(m.chat.id) == 0, content_types=['text'])
def generate_text_handler(message):
    cid = message.chat.id
    db.add_log("user", message.text, cid)
    task_id = service_api.send_text(message.text)
    flag = False
    if task_id is not None:
        bot_text = "Please wait, image is generating"
        bot.send_message(cid, bot_text)
        db.add_image(cid, message.text, task_id)
        db.add_log("bot", bot_text, cid)
        db.update_user_status(cid, 1)
        image = service_api.get_image_loop(task_id)
        if image is None:
            flag = False
        else:
            # db.update_image_status(cid, task_id, 1)
            bot.send_photo(cid, image)
            db.add_log("bot", f"send image with task_id: {task_id}", cid)
            flag = True
    if not flag:
        bot_text = "Something went wrong, please try again later"
        bot.send_message(cid, bot_text)
        db.add_log("bot", bot_text, cid)
    db.update_user_status(cid, 0)


@bot.message_handler(func=lambda m: db.check_user_status(m.chat.id) == 1, content_types=['text'])
def wait_image_handler(message):
    cid = message.chat.id
    db.add_log("user", message.text, cid)
    bot_text = "Please wait, image is generating. Can generate only one image at time"
    bot.send_message(cid, bot_text)
    db.add_log("bot", bot_text, cid)


@bot.message_handler(func=lambda m: db.check_user_status(m.chat.id) == -1, content_types=['text'])
def no_start_handler(message):
    command_start(message)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def command_default(message):
    # this is the standard reply to a normal message
    cid = message.chat.id
    bot_text = "I don't understand \"" + message.text + "\"\nMaybe try the help page at `/help`"
    bot.send_message(cid, bot_text)
    db.add_log("bot", bot_text, cid)


def main():
    bot.infinity_polling()


if __name__ == "__main__":
    main()
