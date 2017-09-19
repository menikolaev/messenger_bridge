import json
import os
from multiprocessing import JoinableQueue

senders = {
    'vk': {},
    'tg': {},
}

queues = {
    'vk': {},
    'tg': {},
}

unique_queues = []


def create_instances():
    for typ, members in chat_mapper.items():
        for id, settings in members['chats'].items():
            creds = settings['credentials']
            senders[typ][id] = chat_mapper[typ]['sender'](creds)

            if str(id) not in queues[typ]:
                queues[typ][str(id)] = JoinableQueue()
                unique_queues.append(queues[typ][str(id)])

            receivers = settings['send_to']
            for receiver in receivers:
                if receiver['id'] not in queues[receiver['type']]:
                    queues[receiver['type']][receiver['id']] = queues[typ][str(id)]


def get_senders():
    return senders


def load_config():
    base = os.path.dirname(os.path.abspath(__name__))
    path = os.path.join(base, 'config.json')
    with open(path, 'r') as f:
        data = f.readlines()
    return json.loads(''.join(data))

chat_mapper = load_config()

