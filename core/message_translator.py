import logging

import time

from core.senders import chat_mapper, senders


class CoreTranslator:
    def get_sender(self, message_to):
        receivers = []
        for receiver in message_to:
            rec_type = receiver['type']
            rid = receiver['id']
            settings = chat_mapper[rec_type]['chats'][rid]
            sender = senders[rec_type].get(rid)
            if not sender:
                credentials = settings['credentials']
                sender_class = chat_mapper[rec_type]['sender']
                sender = sender_class(credentials)
                senders[rec_type][rid] = sender

            receivers.append(sender)
        return receivers

    def get_message_to_send(self, message: dict, message_type):
        forwarded_text = ''
        fwd_func = message.get('fwd_func')
        if fwd_func:
            forwarded_text = fwd_func(chat_mapper[message_type]['forward_format'], message['message_data'])

        text_body = '\n'.join([message['text'], forwarded_text])
        message.update({'message': text_body})

        return chat_mapper[message_type]['message_format'].format(**message)

    def translator(self, message, messenger, from_id: str):
        try:
            message_to = chat_mapper[messenger]['chats'][from_id]['send_to']
        except:
            raise Exception('Cannot find receivers')

        receivers = self.get_sender(message_to)
        for receiver in receivers:
            self.send_message(message, receiver)

    def send_message(self, message, receiver):
        msg = self.get_message_to_send(message, receiver.handler_type)
        for i in range(1, 4):
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
            message_to = chat_mapper[messenger]['chats'][from_id]['send_to']
        except:
            raise Exception('Cannot find receivers')

        receivers = self.get_sender(message_to)
        for receiver in receivers:
            for i in range(1, 4):
                try:
                    receiver.send_image(img_file)
                    break
                except Exception as e:
                    time.sleep(i * 1)
                    logging.info(str(e))
                    print(e)
        img_file.close()


CoreTranslator = CoreTranslator()
