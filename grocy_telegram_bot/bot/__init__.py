import logging
from datetime import timedelta

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, \
    CallbackContext, CallbackQueryHandler
from telegram_click.decorator import command

from grocy_telegram_bot.bot.inline_keyboard_handler import InlineKeyboardHandler
from grocy_telegram_bot.bot.reply_keyboard_handler import ReplyKeyboardHandler
from grocy_telegram_bot.cache import GrocyCached
from grocy_telegram_bot.commands.chore import ChoreCommandHandler
from grocy_telegram_bot.commands.config import ConfigCommandHandler
from grocy_telegram_bot.commands.help import HelpCommandHandler
from grocy_telegram_bot.commands.inventory import InventoryCommandHandler
from grocy_telegram_bot.commands.shopping_list import ShoppingListCommandHandler
from grocy_telegram_bot.commands.stats import StatsCommandHandler
from grocy_telegram_bot.commands.version import VersionCommandHandler
from grocy_telegram_bot.config import Config
from grocy_telegram_bot.const import *
from grocy_telegram_bot.monitoring.monitor import Monitor
from grocy_telegram_bot.notifier import Notifier
from grocy_telegram_bot.permissions import CONFIG_ADMINS
from grocy_telegram_bot.stats import COMMAND_TIME_START
from grocy_telegram_bot.util import send_message, flatten

LOGGER = logging.getLogger(__name__)


class GrocyTelegramBot:
    """
    The main entry class of the grocy telegram bot
    """

    def __init__(self, config: Config):
        """
        Creates an instance.
        :param config: configuration object
        """
        self._config = config

        self._grocy = GrocyCached(
            base_url=f"{config.GROCY_HOST.value}",
            api_key=config.GROCY_API_KEY.value,
            port=config.GROCY_PORT.value)

        self._response_handler = ReplyKeyboardHandler()
        self._keyboard_handler = InlineKeyboardHandler()

        self._updater = Updater(token=self._config.TELEGRAM_BOT_TOKEN.value, use_context=True)
        LOGGER.debug("Using bot id '{}' ({})".format(self._updater.bot.id, self._updater.bot.name))

        self._dispatcher = self._updater.dispatcher

        self._help_command_handler = HelpCommandHandler(self._config, self._grocy, self._response_handler,
                                                        self._keyboard_handler)
        self._grocy_command_handlers = [
            ChoreCommandHandler(self._config, self._grocy, self._response_handler, self._keyboard_handler),
            ConfigCommandHandler(self._config, self._grocy, self._response_handler, self._keyboard_handler),
            self._help_command_handler,
            InventoryCommandHandler(self._config, self._grocy, self._response_handler, self._keyboard_handler),
            ShoppingListCommandHandler(self._config, self._grocy, self._response_handler, self._keyboard_handler),
            StatsCommandHandler(self._config, self._grocy, self._response_handler, self._keyboard_handler),
            VersionCommandHandler(self._config, self._grocy, self._response_handler, self._keyboard_handler)
        ]

        command_handlers = flatten(list(map(lambda x: x.command_handlers(), self._grocy_command_handlers)))

        handler_groups = {
            0: [CallbackQueryHandler(callback=self._keyboard_handler.inline_keyboard_click_callback)],
            1: command_handlers +
               [
                   CommandHandler(COMMAND_START,
                                  filters=(~ Filters.reply) & (~ Filters.forwarded),
                                  callback=self._start_callback),
                   CommandHandler(COMMAND_CHAT_ID,
                                  filters=(~ Filters.reply) & (~ Filters.forwarded),
                                  callback=self._chat_id_callback),

                   CommandHandler(CANCEL_KEYBOARD_COMMAND[1:],
                                  filters=(~ Filters.reply) & (~ Filters.forwarded),
                                  callback=self._response_handler.cancel_keyboard_callback),
                   # unknown command handler
                   MessageHandler(
                       filters=Filters.command & (~ Filters.forwarded),
                       callback=self._unknown_command_callback),
                   MessageHandler(
                       filters=(~ Filters.forwarded),
                       callback=self._any_message_callback),
               ]
        }

        for group, handlers in handler_groups.items():
            for handler in handlers:
                self._updater.dispatcher.add_handler(handler, group=group)

        self._monitor = None
        chat_ids = self._config.NOTIFICATION_CHAT_IDS.value
        if chat_ids is not None and len(chat_ids) > 0:
            self._notifier = Notifier(self._updater, chat_ids)
            interval = self._config.GROCY_CACHE_DURATION.value + timedelta(seconds=1)
            self._monitor = Monitor(interval, self._notifier, self._grocy)

    @property
    def bot(self):
        return self._updater.bot

    def start(self):
        """
        Starts up the bot.
        """
        if self._monitor is not None:
            self._monitor.start()
        self._updater.start_polling()
        self._updater.idle()

    def stop(self):
        """
        Shuts down the bot.
        """
        if self._monitor is not None:
            self._monitor.stop()
        self._updater.stop()

    @COMMAND_TIME_START.time()
    def _start_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Welcomes a new user with a greeting message
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id
        user_first_name = update.effective_user.first_name

        if not CONFIG_ADMINS.evaluate(update, context):
            send_message(bot, chat_id, "Sorry, you do not have permissions to use this bot.")
            return

        send_message(bot, chat_id,
                     f"Welcome {user_first_name},\nthis is your grocy-telegram-bot instance, ready to go!")

    @command(
        name=COMMAND_CHAT_ID,
        description="Show current chat id.",
        permissions=CONFIG_ADMINS
    )
    def _chat_id_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Print the current chat id, to make it easier to add it to notifications
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id
        send_message(bot, chat_id, f"{chat_id}", parse_mode=ParseMode.MARKDOWN)

    def _unknown_command_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Handles unknown commands send by a user
        :param update: the chat update object
        :param context: telegram context
        """
        message = update.effective_message
        username = "N/A"
        if update.effective_user is not None:
            username = update.effective_user.username

        user_is_admin = username in self._config.TELEGRAM_ADMIN_USERNAMES.value
        if user_is_admin:
            self._help_command_handler.help_command_callback(update, context)
            return

    def _any_message_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Used to respond to response keyboard entry selections
        :param update: the chat update object
        :param context: telegram context
        """
        self._response_handler.on_message(update, context)
