from adapters.telegram.telegram_reciever import start_bot
from adapters.vk.vk_reciever import start_vk
from core.senders import create_instances

if __name__ == '__main__':
    create_instances()
    start_vk()
    start_bot()
