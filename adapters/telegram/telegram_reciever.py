import threading

import telebot
from multiprocessing import JoinableQueue, Process

from adapters.telegram import config
from core.base_handler import BaseHandler
from core.message_translator import CoreTranslator
from core.senders import chat_mapper

bot = telebot.TeleBot(config.token)

q = JoinableQueue()


@bot.message_handler(func=lambda message: True, content_types=["text"])
def handle_message(message):
    if str(message.chat.id) not in chat_mapper['tg']['chats']:
        bot.send_message(message.chat.id, 'This chat is not in a group of permitted chats')
        return

    q.put(message)


def get_fwd_message(msg_format, message):
    text = ""
    if message.forward_from:
        user_name = get_user_name(message)
        text += msg_format.format(user_name=user_name, message=message.text)
    elif message.reply_to_message:
        user_name = get_user_name(message.reply_to_message)
        text += msg_format.format(user_name=user_name, message=message.reply_to_message.text)
    return text


def get_user_name(message):
    if message.from_user.first_name or message.from_user.last_name:
        user_name = "{} {}".format(message.from_user.first_name or '', message.from_user.last_name or '')
    else:
        user_name = "{}".format(message.from_user.username)
    return ' '.join([x for x in user_name.split(' ') if x])


def construct_message(message):
    user_name = get_user_name(message)

    return {
        'user_name': user_name,
        'message_data': message,
        'text': message.text,
        'fwd_func': get_fwd_message
    }


def message_loop(queue):
    while True:
        message = queue.get()
        text = construct_message(message)
        try:
            CoreTranslator.translator(text, 'tg', str(message.chat.id))
        except:
            bot.send_message(message.chat.id, 'Bot unavailable')
        queue.task_done()


class TelegramHandler(BaseHandler):
    handler_type = 'tg'

    def __init__(self, credentials):
        super().__init__(credentials)
        self.chat_id = credentials['chat_id']

    def send(self, message, attachments=None):
        bot.send_message(self.chat_id, message, parse_mode='html')


chat_mapper['tg']['sender'] = TelegramHandler


def start_bot():
    loop = Process(target=message_loop, args=(q,))
    loop.start()
    bot.polling(none_stop=True)
    q.join()
