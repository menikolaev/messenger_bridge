import telebot


class NonFailBot(telebot.TeleBot):
    def get_updates(self, offset=None, limit=None, timeout=20, allowed_updates=None):
        """
        Use this method to receive incoming updates using long polling (wiki). An Array of Update objects is returned.
        :param allowed_updates: Array of string. List the types of updates you want your bot to receive.
        :param offset: Integer. Identifier of the first update to be returned.
        :param limit: Integer. Limits the number of updates to be retrieved.
        :param timeout: Integer. Timeout in seconds for long polling.
        :return: array of Updates
        """
        try:
            return super().get_updates(offset, limit, timeout, allowed_updates)
        except Exception as e:
            telebot.logger.fatal('Issues when getting info from telegram: {}', str(e))
