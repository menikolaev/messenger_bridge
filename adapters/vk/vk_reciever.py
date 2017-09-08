import logging
import multiprocessing

import time
from functools import partial

import vk

from core.base_handler import BaseHandler
from core.message_translator import CoreTranslator
from core.senders import chat_mapper, get_senders

PEER_ID_START = 2000000000
user_names = {}


class VKHandler(BaseHandler):
    handler_type = 'vk'

    def __init__(self, credentials: dict, api_version='5.68', api_language='ru', api_timeout=10):
        # Параметры для регистрации
        super().__init__(credentials)
        self.user_login = credentials['user_login']
        self.user_password = credentials['user_password']
        self.scope = credentials['scope']
        self.app_id = credentials['app_id']
        # Параметры для отправки
        self.chat_id = credentials.get('chat_id')
        self.user_id = credentials.get('user_id')
        # Внутренние объекты VK
        self.session = vk.AuthSession(self.app_id, self.user_login, self.user_password, self.scope)
        self.api = vk.API(self.session, v=api_version, lang=api_language, timeout=api_timeout)
        self.last_message_id = self.get_last_message_id()
        # self.long_polling = self.get_pts()

    # def get_pts(self):
    #     result = self.api.messages.getLongPollServer(need_pts=1, lp_version=2)
    #     return result['pts']

    def get_last_message_id(self):
        if self.user_id:
            result = self.api.messages.getHistory(user_id=self.user_id, count=1)
        elif self.chat_id:
            result = self.api.messages.getHistory(peer_id=PEER_ID_START + self.chat_id, count=1)
        else:
            raise ValueError('None of chat_id or user_id was set')

        if result.get('error_msg'):
            raise ValueError('Error on response: {}'.format(result['error_msg']))

        return result['items'][0]['id']

    def send(self, message, attachments=None):
        if self.user_id:
            result = self.api.messages.send(user_id=self.user_id, message=message)
        elif self.chat_id:
            result = self.api.messages.send(chat_id=self.chat_id, message=message)
        else:
            raise ValueError('None of chat_id or user_id was set')

        self._check_result(result)

    def _check_result(self, result):
        if not isinstance(result, dict):
            return
        error = result.get('error_msg')
        if error:
            raise Exception('Error while sending a message')


def get_fwd_message(msg_format, message, handler: VKHandler):
    fwd_messages = message.get('fwd_messages')
    if not fwd_messages:
        return ''
    text = ""
    for forwarded in fwd_messages:
        if forwarded['user_id'] not in user_names:
            get_user_names([message], handler)
        user_name = user_names[forwarded['user_id']]
        msg = '\n'.join([forwarded['body'], get_fwd_message(msg_format, forwarded, handler) or ''])
        # if not msg:
        #     msg = forwarded['body'] or ''
        text += msg_format.format(user_name=user_name, message=msg)
    return text


def construct_message(message, handler: VKHandler):
    return {
        'user_name': user_names[message['user_id']],
        'message_data': message,
        'text': message['body'],
        'fwd_func': partial(get_fwd_message, handler=handler)
    }


def get_user_names(messages, handler: VKHandler):
    cleared_user_ids = [str(x['user_id']) for x in messages if x['user_id'] not in user_names]
    result = []
    for i in range(1, 4):
        try:
            result = handler.api.users.get(user_ids=','.join(cleared_user_ids))
            break
        except Exception as e:
            print(e)

    for item in result:
        user_names[item['id']] = "{} {}".format(item['first_name'], item['last_name'])


def receive_messages():
    # TODO: переписать на getDialog, чтобы не нагружать другие чатики
    while True:
        handlers = get_senders()['vk']

        for vk_handler in handlers.values():
            try:
                if vk_handler.user_id:
                    result = vk_handler.api.messages.getHistory(user_id=vk_handler.user_id, count=30)
                elif vk_handler.chat_id:
                    result = vk_handler.api.messages.getHistory(peer_id=PEER_ID_START + vk_handler.chat_id, count=30)
                else:
                    raise ValueError('None of chat_id or user_id was set')

                raw_messages = [x for x in result['items'] if
                                x['id'] > vk_handler.last_message_id and (x['out'] == 1 or x['random_id'] > 0)]
                if not raw_messages:
                    continue
                messages = sorted(raw_messages, key=lambda x: x['id'])

                get_user_names(messages, vk_handler)

                CoreTranslator.send_many(messages=[construct_message(x, vk_handler) for x in messages],
                                         messenger='vk',
                                         from_id=str(vk_handler.user_id or vk_handler.chat_id))

                vk_handler.last_message_id = messages[-1]['id']

            except Exception as e:
                logging.info(str(e))
                print(e)

        time.sleep(1.5)


def start_vk():
    vk_listener = multiprocessing.Process(target=receive_messages)
    vk_listener.start()


chat_mapper['vk']['sender'] = VKHandler

if __name__ == '__main__':
    credentials = dict(app_id=0, user_login='********', user_password='********',
                       scope='messages', user_id=0)
    handler = VKHandler(credentials)
    print(handler.get_last_message_id())
    handler.send('test')
