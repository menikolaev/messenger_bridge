import traceback
from multiprocessing import Process

import time

from core.message_translator import CoreTranslator
from core.senders import unique_queues


def message_loop():
    while True:
        for queue in unique_queues:
            try:
                if queue.empty():
                    continue

                data = queue.get(block=False)

                if data['type'] == 'text':
                    CoreTranslator.translator(data['message'], data['messenger'], data['from_id'])
                elif data['type'] == 'image':
                    CoreTranslator.send_image(data['message'], data['messenger'], data['from_id'])

                queue.task_done()
            except Exception as e:
                traceback.print_tb(e.__traceback__)
        time.sleep(1)


def start_message_loop():
    process = Process(target=message_loop)
    process.start()
