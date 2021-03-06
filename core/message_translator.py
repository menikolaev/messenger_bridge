import logging
import time

from core.senders import chat_mapper, senders, spawn_class
from modules.main import where_lessons


class CoreTranslator:
    def get_sender(self, message_to):
        receivers = []
        for receiver in message_to:
            rec_type = receiver['type']
            rid = receiver['id']
            settings = chat_mapper['messengers'][rec_type]['chats'][rid]
            sender = senders[rec_type].get(rid)
            if not sender:
                credentials = settings['credentials']
                sender_class = chat_mapper['messengers'][rec_type]['sender']
                sender = sender_class(credentials)
                senders[rec_type][rid] = sender

            receivers.append(sender)
        return receivers

    def check_modules(self, message):
        result = where_lessons(message=message['text'])
        return result

    def get_message_to_send(self, message: dict, message_type):
        fwd_func = message.get('fwd_func')
        if fwd_func:
            forwarded_text = fwd_func(chat_mapper['messengers'][message_type]['forward_format'])
            text_body = '\n'.join([message['text'], forwarded_text])
        else:
            text_body = message['text']
        message.update({'message': text_body})

        return chat_mapper['messengers'][message_type]['message_format'].format(**message)

    def translator(self, message, messenger, from_id: str):
        try:
            message_to = chat_mapper['messengers'][messenger]['chats'][from_id]['send_to']
        except:
            raise Exception('Cannot find receivers')

        receivers = self.get_sender(message_to)

        for receiver in receivers:
            self.send_message(message, receiver)

        process = spawn_class(target=self.handle_modules, args=(message, messenger, from_id, receivers,))
        process.start()

    def handle_modules(self, message, messenger, from_id, receivers):
        result = self.check_modules(message)
        if result:
            # Текущему пользователю
            to = [{'type': messenger, 'id': from_id}]
            first_receiver = self.get_sender(to)[0]
            self.send_message(result, first_receiver)

            # Другие получатели
            for receiver in receivers:
                self.send_message(result, receiver)

    def send_message(self, message, receiver):
        msg = self.get_message_to_send(message, receiver.handler_type)
        for i in range(1, 6):
            try:
                receiver.send(msg)
                break
            except Exception as e:
                time.sleep(i * 1)
                logging.info(str(e))
                print(e)

    def send_many(self, messages, messenger, from_id: str):
        for message in messages:
            self.translator(message, messenger, from_id)

    def send_image(self, img_file, messenger, from_id: str):
        try:
            message_to = chat_mapper['messengers'][messenger]['chats'][from_id]['send_to']
        except:
            raise Exception('Cannot find receivers')

        receivers = self.get_sender(message_to)
        for receiver in receivers:
            for i in range(1, 6):
                try:
                    receiver.send_image(img_file)
                    break
                except Exception as e:
                    time.sleep(i * 1)
                    logging.info(str(e))
                    print(e)
        img_file.close()


CoreTranslator = CoreTranslator()
