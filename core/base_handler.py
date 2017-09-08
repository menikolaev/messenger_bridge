class BaseHandler:
    handler_type = None

    def __init__(self, credentials):
        pass

    def send(self, message, attachments=None):
        raise NotImplementedError
