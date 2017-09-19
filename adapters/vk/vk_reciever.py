import datetime
import json
import logging
import multiprocessing
import time
from multiprocessing import Value

import requests
import vk
from vk import API

from adapters.vk.message import Message
from core.base_handler import BaseHandler
from core.message_translator import CoreTranslator
from core.senders import chat_mapper, get_senders

user_names = {}
PEER_ID_START = 2000000000


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
        self.chat_group_id = credentials.get('chat_group_id')
        self.user_id = credentials.get('user_id')
        # Внутренние объекты VK
        self.api = API(self.session, v=api_version, lang=api_language, timeout=api_timeout)
        self.last_message_id = Value('i', self.get_last_message_id())

    def get_last_message_id(self):
        if self.user_id:
            result = self.api.messages.getDialogs(count=1)
        else:
            raise ValueError('None of chat_id or user_id was set')

        if result.get('error_msg'):
            raise ValueError('Error on response: {}'.format(result['error_msg']))

        return result['items'][0]['message']['id']

    def send(self, message, attachment=None):
        with self.last_message_id.get_lock():
            if self.chat_group_id:
                peer_id = PEER_ID_START + self.chat_group_id
            elif self.chat_id:
                peer_id = self.chat_id
            else:
                raise ValueError('None of chat_id or user_id was set')

            result = self.api.messages.send(peer_id=peer_id, message=message, attachment=attachment)

            self._check_result(result)
            self.last_message_id.value = result

    def _check_result(self, result):
        if not isinstance(result, dict):
            return
        error = result.get('error_msg')
        if error:
            raise Exception('Error while sending a message')

    def send_image(self, img_file):
        upload_server = self.api.photos.getMessagesUploadServer(peer_id=self.user_id)
        link = upload_server['upload_url']
        timestamp = int(datetime.datetime.now().timestamp())
        result = requests.post(url=link,
                               files={'photo': ('photo_{}.png'.format(timestamp), img_file)})
        content = json.loads(result.content)
        photos = self.api.photos.saveMessagesPhoto(photo=content['photo'], hash=content['hash'],
                                                   server=content['server'])
        self.send(message=None, attachment=['photo{}_{}'.format(photos[0]['owner_id'], photos[0]['id'])])


def construct_message(message):
    return {
        'user_name': message.user_name,
        'text': message.text,
        'fwd_func': message.get_fwd_message
    }


def get_user_names(messages, handler: VKHandler):
    cleared_user_ids = []
    flat_messages = []
    for msg in messages:
        flat_tree = msg.flat_messages_tree
        flat_messages.extend(flat_tree)
        cleared_user_ids.extend([str(x.from_id or x.user_id) for x in flat_tree
                                 if (x.from_id or x.user_id) not in user_names])
    result = []
    for i in range(1, 6):
        try:
            result = handler.api.users.get(user_ids=','.join(cleared_user_ids))
            break
        except Exception as e:
            print(e)

    for item in result:
        user_name = "{} {}".format(item['first_name'], item['last_name'])
        if item['id'] not in user_names:
            user_names[item['id']] = user_name

    for uid, name in user_names.items():
        filtered_messages = list(filter(lambda x: (x.from_id or x.user_id) == uid, flat_messages))
        for msg in filtered_messages:
            msg.user_name = name


def get_raw_messages(vk_handler):
    if vk_handler.chat_group_id:
        result = vk_handler.api.messages.getHistory(peer_id=PEER_ID_START + vk_handler.chat_group_id, count=30)
    elif vk_handler.chat_id:
        result = vk_handler.api.messages.getHistory(peer_id=vk_handler.chat_id, count=30)
    else:
        raise ValueError('None of chat_id or user_id was set')

    new_messages = [x for x in result['items'] if x['id'] > vk_handler.last_message_id.value]

    cleared = []
    for message_data in new_messages:
        cleared.append(Message(message_data))
    return cleared


def receive_messages(queue):
    # TODO: переписать на getDialog, чтобы не нагружать другие чатики
    while True:
        handlers = get_senders()['vk']

        for id, vk_handler in handlers.items():
            try:
                with vk_handler.last_message_id.get_lock():
                    raw_messages = get_raw_messages(vk_handler)

                if not raw_messages:
                    continue

                messages = sorted(raw_messages, key=lambda x: x.id)

                get_user_names(messages, vk_handler)

                for item in messages:
                    message = {
                        'message': construct_message(item),
                        'from_id': str(vk_handler.chat_id or vk_handler.chat_group_id)
                    }
                    queue.put(message)

            except Exception as e:
                logging.info(str(e))
                print(e)
            else:
                try:
                    # Если last_message_id > messages[-1], то не обновляем
                    with vk_handler.last_message_id.get_lock():
                        if vk_handler.last_message_id.value < messages[-1].id:
                            vk_handler.last_message_id.value = messages[-1].id
                except:
                    print('Unable to get last_message_id')

        time.sleep(1.5)


def message_sender(queue):
    while True:
        data = queue.get()
        CoreTranslator.translator(message=data['message'], messenger='vk', from_id=data['from_id'])
        queue.task_done()


def start_vk():
    manager = multiprocessing.Manager()
    queue = manager.JoinableQueue()
    vk_consumer = multiprocessing.Process(target=message_sender, args=(queue,))
    vk_consumer.start()
    vk_listener = multiprocessing.Process(target=receive_messages, args=(queue,))
    vk_listener.start()


chat_mapper['vk']['sender'] = VKHandler

if __name__ == '__main__':
    credentials = dict(app_id=0, user_login='********', user_password='********',
                       scope='messages', user_id=0)
    handler = VKHandler(credentials)
    print(handler.get_last_message_id())
    handler.send('test')
