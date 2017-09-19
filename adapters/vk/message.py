import html


class Message:
    def __init__(self, vk_message: dict):
        self.id = vk_message.get('id')
        self.body = vk_message.get('body')
        self.user_id = vk_message.get('user_id')
        self.from_id = vk_message.get('from_id')
        self.date = vk_message.get('date')
        self.read_state = vk_message.get('read_state')
        self.out = vk_message.get('out')
        self.chat_id = vk_message.get('chat_id')
        self.attachments = vk_message.get('attachments')
        self.user_name = None

        self.fwd_messages = self.build_forwarded_messages(vk_message.get('fwd_messages'))

    @property
    def text(self):
        text = self.body
        attachments = []
        if self.attachments:
            for attachment in self.attachments:
                if attachment['type'] == 'doc':
                    attachments.append(attachment[attachment['type']]['url'])
                elif attachment['type'] == 'photo':
                    attachments.append(attachment[attachment['type']]['photo_604'])
                elif attachment['type'] == 'sticker':
                    attachments.append(attachment[attachment['type']]['photo_352'])
                else:
                    continue
            return html.escape('\n'.join([text, '\n'.join(attachments)]))

        return html.escape(text)

    def get_fwd_message(self, fwd_msg_format):
        fwd_messages = self.fwd_messages
        if not fwd_messages:
            return ''
        text = ""
        for forwarded in fwd_messages:
            msg = '\n'.join([forwarded.text, forwarded.get_fwd_message(fwd_msg_format) or ''])
            text += fwd_msg_format.format(user_name=forwarded.user_name, message=msg)
        return text

    def build_forwarded_messages(self, forwarded_messages):
        if not forwarded_messages:
            return None

        messages = []
        for forwarded_data in forwarded_messages:
            messages.append(Message(forwarded_data))

        return messages

    @property
    def flat_messages_tree(self):
        flat_tree = [self]

        if self.fwd_messages:
            for forwarded in self.fwd_messages:
                flat_tree.extend(forwarded.flat_messages_tree)

        return flat_tree
