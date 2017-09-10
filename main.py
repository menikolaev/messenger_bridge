from flask import Flask

from adapters.telegram.telegram_reciever import start_bot
from adapters.vk.vk_reciever import start_vk
from core.senders import create_instances

app = Flask('translator')
app.config.from_pyfile('config.py')


@app.route('/')
def webhook_handler():
    pass


if __name__ == '__main__':
    # app.run(host='127.0.0.1', port=8000)
    create_instances()
    start_vk()
    start_bot()
