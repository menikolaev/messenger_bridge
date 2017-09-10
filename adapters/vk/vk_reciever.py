import logging
import multiprocessing

import time
from functools import partial

import requests
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
        if 'auth_token' in credentials:
            self.auth_token = credentials['auth_token']
            self.session = vk.Session(self.auth_token)
        else:
            self.user_login = credentials['user_login']
            self.user_password = credentials['user_password']
            self.scope = credentials['scope']
            self.app_id = credentials['app_id']
            self.session = vk.AuthSession(self.app_id, self.user_login, self.user_password, self.scope)
        # Параметры для отправки
        self.chat_id = credentials.get('chat_id')
        self.user_id = credentials.get('user_id')
        # Внутренние объекты VK
        self.api = vk.API(self.session, v=api_version, lang=api_language, timeout=api_timeout)
        self.last_message_id = self.get_last_message_id()

    def get_last_message_id(self):
        if self.user_id:
            result = self.api.messages.getDialogs(count=1)
        else:
            raise ValueError('None of chat_id or user_id was set')

        if result.get('error_msg'):
            raise ValueError('Error on response: {}'.format(result['error_msg']))

        return result['items'][0]['message']['id']

    def send(self, message, attachments=None):
        if self.chat_id:
            result = self.api.messages.send(user_id=self.chat_id, message=message)
        else:
            raise ValueError('None of chat_id or user_id was set')

        self._check_result(result)

    def _check_result(self, result):
        if not isinstance(result, dict):
            return
        error = result.get('error_msg')
        if error:
            raise Exception('Error while sending a message')

    def send_image(self, img_file):
        upload_server = self.api.photos.getMessagesUploadServer(peer_id=self.user_id)
        link = upload_server['upload_url']
        result = requests.post(link, files={'photo': img_file}, headers={'Content-Type': 'multipart/form-data'})
        print(result)


def get_fwd_message(msg_format, message, handler: VKHandler):
    fwd_messages = message.get('fwd_messages')
    if not fwd_messages:
        return ''
    text = ""
    for forwarded in fwd_messages:
        if forwarded['user_id'] not in user_names:
            get_user_names([message], handler)
        user_name = user_names[forwarded['user_id']]
        msg = '\n'.join([construct_text(forwarded), get_fwd_message(msg_format, forwarded, handler) or ''])
        text += msg_format.format(user_name=user_name, message=msg)
    return text


def construct_text(message):
    text = message['body']
    attachments_data = message.get('attachments')
    attachments = []
    if attachments_data:
        for attachment in attachments_data:
            if attachment['type'] == 'doc':
                attachments.append(attachment[attachment['type']]['url'])
            elif attachment['type'] == 'photo':
                attachments.append(attachment[attachment['type']]['photo_604'])
            elif attachment['type'] == 'sticker':
                attachments.append(attachment[attachment['type']]['photo_352'])
            else:
                continue
    return '{}\n{}'.format(text, '\n'.join(attachments))


def construct_message(message, handler: VKHandler):
    return {
        'user_name': user_names[message['from_id']],
        'message_data': message,
        'text': construct_text(message),
        'fwd_func': partial(get_fwd_message, handler=handler)
    }


def get_user_names(messages, handler: VKHandler):
    cleared_user_ids = [str(x['from_id']) for x in messages if x['from_id'] not in user_names]
    result = []
    for i in range(1, 4):
        try:
            result = handler.api.users.get(user_ids=','.join(cleared_user_ids))
            break
        except Exception as e:
            print(e)

    for item in result:
        user_names[item['id']] = "{} {}".format(item['first_name'], item['last_name'])


def get_raw_messages(ids, vk_handler):
    result = vk_handler.api.messages.getHistory(user_id=vk_handler.chat_id)
    cleared = []
    for id in ids:
        for item in result['items']:
            if id == item['id']:
                cleared.append(item)
    return cleared


def receive_messages():
    # TODO: переписать на getDialog, чтобы не нагружать другие чатики
    while True:
        handlers = get_senders()['vk']

        for vk_handler in handlers.values():
            try:
                result = vk_handler.api.messages.getDialogs(count=30)

                new_messages = [x['message']['id'] for x in result['items']
                                if x['message']['id'] > vk_handler.last_message_id and
                                x['message']['user_id'] == vk_handler.chat_id and
                                x['message']['random_id'] > 0]

                if not new_messages:
                    continue

                raw_messages = get_raw_messages(new_messages, vk_handler)

                messages = sorted(raw_messages, key=lambda x: x['id'])

                get_user_names(messages, vk_handler)

                CoreTranslator.send_many(messages=[construct_message(x, vk_handler) for x in messages],
                                         messenger='vk',
                                         from_id=str(vk_handler.chat_id))
            except Exception as e:
                logging.info(str(e))
                print(e)
            else:
                try:
                    vk_handler.last_message_id = messages[-1]['id']
                except:
                    print('Unable to get last_message_id')

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
