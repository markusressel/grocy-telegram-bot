from telegram.ext import Updater

from grocy_telegram_bot.config import Config
from grocy_telegram_bot.util import send_message


class Notifier:

    def __init__(self, config: Config, updater: Updater):
        self._config = config
        self._updater = updater

    def notify(self, message: str):
        """
        Send notification to all enabled chats
        :param message: the message to send
        """
        # TODO: get chat_ids from config (or persistence?)
        chat_ids = []

        for chat_id in chat_ids:
            send_message(self._updater.bot, chat_id, message)
