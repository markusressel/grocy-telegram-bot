from typing import List, Dict

from pygrocy import Grocy
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Handler

from grocy_telegram_bot.config import Config
from grocy_telegram_bot.const import CANCEL_KEYBOARD_COMMAND


class GrocyCommandHandler:

    def __init__(self, config: Config, grocy: Grocy):
        self._config = config
        self._grocy = grocy

    def command_handlers(self) -> List[Handler]:
        """
        :return: a list of all command handlers
        """
        raise NotImplementedError()


def build_reply_keyboard(items: List[str]) -> ReplyKeyboardMarkup:
    """
    Builds a menu to select an item from a list
    :param items: list of items to choose from
    :return: reply markup
    """
    items.append(CANCEL_KEYBOARD_COMMAND)
    keyboard = list(map(lambda x: KeyboardButton(x), items))
    # NOTE: the "selective=True" requires the menu to be sent as a reply
    # (or with an @username mention)
    return ReplyKeyboardMarkup.from_column(keyboard, one_time_keyboard=True, selective=True)


def build_inline_keyboard(items: Dict[str, str]) -> InlineKeyboardMarkup:
    """
    Builds an inline button menu
    :param items: dictionary of "button text" -> "callback data" items
    :return: reply markup
    """
    keyboard = list(map(lambda x: InlineKeyboardButton(x[0], callback_data=x[1]), items.items()))
    return InlineKeyboardMarkup.from_column(keyboard)
