from typing import List

from telegram.ext import Updater

from grocy_telegram_bot.util import send_message


class Notifier:

    def __init__(self, updater: Updater, chat_ids: List[str]):
        self._chat_ids = chat_ids
        self._updater = updater

    def notify(self, message: str):
        """
        Send notification to all enabled chats
        :param message: the message to send
        """
        for chat_id in self._chat_ids:
            send_message(self._updater.bot, chat_id, message)
