chat_mapper = {
    'tg': {
        'chats': {
            '*******': {
                'credentials': {
                    'chat_id': 0
                },
                'send_to': [
                    {
                        'type': 'vk',
                        'id': '******'
                    }
                ]
            }
        },
        'message_format': "<b>{user_name}</b>: {message}",
        'forward_format': "<b>Forwarded from {user_name}</b>:\n{message}"
    },
    'vk': {
        'chats': {
            '******': {
                'credentials': {
                    'user_login': '*********',
                    'user_password': '*******',
                    'app_id': 0,
                    'scope': 'messages',
                    'user_id': 0
                },
                'send_to': [
                    {
                        'type': 'tg',
                        'id': '**********'
                    }
                ]
            }
        },
        'message_format': "FROM {user_name}:\n{message}",
        'forward_format': "Forwarded from {user_name}:\n{message}"
    }
}

senders = {
    'vk': {},
    'tg': {},
}


def create_instances():
    for typ, members in chat_mapper.items():
        for id, settings in members['chats'].items():
            creds = settings['credentials']
            senders[typ][id] = chat_mapper[typ]['sender'](creds)


def get_senders():
    return senders
