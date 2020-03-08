from typing import List

from telegram.ext import Handler

from grocy_telegram_bot.bot import ReplyKeyboardHandler, InlineKeyboardHandler
from grocy_telegram_bot.cache import GrocyCached
from grocy_telegram_bot.config import Config


class GrocyCommandHandler:

    def __init__(self, config: Config, grocy: GrocyCached, reply_keyboard_handler: ReplyKeyboardHandler,
                 inline_keyboard_handler: InlineKeyboardHandler):
        self._config = config
        self._grocy = grocy
        self._reply_keyboard_handler = reply_keyboard_handler
        self._inline_keyboard_handler = inline_keyboard_handler

    def command_handlers(self) -> List[Handler]:
        """
        :return: a list of all command handlers
        """
        raise NotImplementedError()
