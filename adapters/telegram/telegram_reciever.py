from io import BytesIO
from multiprocessing import JoinableQueue, Process

from PIL import Image

from adapters.telegram import config
from adapters.telegram.bot import NonFailBot
from core.base_handler import BaseHandler
from core.message_translator import CoreTranslator
from core.senders import chat_mapper

bot = NonFailBot(config.token)

q = JoinableQueue()


@bot.message_handler(func=lambda message: True, content_types=['text', 'sticker', 'document', 'photo'])
def handle_message(message):
    if str(message.chat.id) not in chat_mapper['tg']['chats']:
        bot.send_message(message.chat.id, 'This chat is not in a group of permitted chats')
        return

    q.put(message)


def webp_to_jpg(webp_file_content):
    with BytesIO(webp_file_content) as f:
        image = Image.open(f).convert('RGB')
    jpeg = BytesIO()
    image.save(jpeg, 'jpeg')
    return jpeg


def construct_text(message):
    text = message.text
    # TODO: сделать нормальную пересылку, не ссылочную
    if message.document:
        file_info = bot.get_file(message.document.file_id)
        url = 'https://api.telegram.org/file/bot{0}/{1}'.format(config.token, file_info.file_path)
        text = 'File name: {}\n{}'.format(message.document.file_name, url)
    elif message.sticker:
        text = message.sticker.emoji
    elif message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        url = 'https://api.telegram.org/file/bot{0}/{1}'.format(config.token, file_info.file_path)
        text = 'File size: {} (KB)\nCaption: {}\n{}'.format(message.photo[-1].file_size // 1024,
                                                            message.caption or 'Empty',
                                                            url)
    return text


def get_fwd_message(msg_format, message):
    text = ""
    if message.forward_from:
        user_name = get_user_name(message)
        text += msg_format.format(user_name=user_name, message=construct_text(message))
    elif message.reply_to_message:
        user_name = get_user_name(message.reply_to_message)
        text += msg_format.format(user_name=user_name, message=construct_text(message.reply_to_message))
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
        'text': construct_text(message),
        'fwd_func': get_fwd_message
    }


def send_text(message):
    text = construct_message(message)
    try:
        CoreTranslator.translator(text, 'tg', str(message.chat.id))
    except:
        bot.send_message(message.chat.id, 'Bot unavailable')


def message_loop(queue):
    while True:
        message = queue.get()
        if message.content_type == 'text':
            send_text(message)
        elif message.content_type == 'sticker':
            send_text(message)
            # file_info = bot.get_file(message.sticker.file_id)
            # file = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(config.token, file_info.file_path))
            # jpeg = webp_to_jpg(file.content)
            # try:
            #     CoreTranslator.send_image(jpeg, 'tg', str(message.chat.id))
            # except:
            #     bot.send_message(message.chat.id, 'Bot unavailable')
        else:
            send_text(message)

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
