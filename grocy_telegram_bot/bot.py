import logging

from telegram import Update, ParseMode
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, \
    CallbackContext
from telegram_click.decorator import command
from telegram_click.permission import PRIVATE_CHAT
from telegram_click.permission.base import Permission

from grocy_telegram_bot.config import Config
from grocy_telegram_bot.stats import format_metrics, START_TIME
from grocy_telegram_bot.util import send_message

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

COMMAND_START = "start"
COMMAND_STATS = 'stats'

COMMAND_COMMANDS = ['help', 'h']
COMMAND_VERSION = ['version', 'v']
COMMAND_CONFIG = ['config', 'c']


class _ConfigAdmins(Permission):

    def __init__(self):
        self._config = Config(validate=False)

    def evaluate(self, update: Update, context: CallbackContext) -> bool:
        from_user = update.effective_message.from_user
        return from_user.username in self._config.TELEGRAM_ADMIN_USERNAMES.value


CONFIG_ADMINS = _ConfigAdmins()


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

        self._updater = Updater(token=self._config.TELEGRAM_BOT_TOKEN.value, use_context=True)
        LOGGER.debug("Using bot id '{}' ({})".format(self._updater.bot.id, self._updater.bot.name))

        self._dispatcher = self._updater.dispatcher

        handlers = [
            CommandHandler(COMMAND_START,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._start_callback),
            CommandHandler(COMMAND_STATS,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._stats_callback),
            CommandHandler(COMMAND_VERSION,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._version_command_callback),
            CommandHandler(COMMAND_CONFIG,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._config_command_callback),
            CommandHandler(COMMAND_COMMANDS,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._commands_command_callback),
            # unknown command handler
            MessageHandler(
                filters=Filters.command & (~ Filters.forwarded),
                callback=self._unknown_command_callback),
        ]

        for handler in handlers:
            self._updater.dispatcher.add_handler(handler)

    @property
    def bot(self):
        return self._updater.bot

    def start(self):
        """
        Starts up the bot.
        This means filling the url pool and listening for messages.
        """
        self._updater.start_polling()
        self._updater.idle()

    def stop(self):
        """
        Shuts down the bot.
        """
        self._updater.stop()

    @START_TIME.time()
    def _start_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Welcomes a new user with an example image and a greeting message
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id
        send_message(bot, chat_id, "Not implemented")

    @command(
        name=COMMAND_STATS,
        description="List statistics of this bot.",
        permissions=CONFIG_ADMINS
    )
    def _stats_callback(self, update: Update, context: CallbackContext) -> None:
        """
        /stats command handler
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        message = update.effective_message
        chat_id = update.effective_chat.id

        text = format_metrics()

        send_message(bot, chat_id, text, reply_to=message.message_id)

    @command(
        name=COMMAND_VERSION,
        description="Show the version of this bot.",
        permissions=CONFIG_ADMINS
    )
    def _version_command_callback(self, update: Update, context: CallbackContext) -> None:
        """
        /stats command handler
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        message = update.effective_message
        chat_id = update.effective_chat.id

        from grocy_telegram_bot import __version__
        text = "{}".format(__version__)
        send_message(bot, chat_id, text, reply_to=message.message_id)

    @command(
        name=COMMAND_CONFIG,
        description="Show current application configuration.",
        permissions=PRIVATE_CHAT & CONFIG_ADMINS
    )
    def _config_command_callback(self, update: Update, context: CallbackContext):
        """
        /config command handler
        :param update: the chat update object
        :param context: telegram context
        """
        from container_app_conf.formatter.toml import TomlFormatter

        bot = context.bot
        chat_id = update.effective_message.chat_id
        message_id = update.effective_message.message_id

        text = self._config.print(formatter=TomlFormatter())
        text = "```\n{}\n```".format(text)
        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN, reply_to=message_id)

    @command(
        name=COMMAND_COMMANDS,
        description="List commands supported by this bot.",
        permissions=CONFIG_ADMINS
    )
    def _commands_command_callback(self, update: Update, context: CallbackContext):
        bot = context.bot
        message = update.effective_message
        chat_id = update.effective_chat.id

        from telegram_click import generate_command_list
        text = generate_command_list(update, context)
        send_message(bot, chat_id, text,
                     parse_mode=ParseMode.MARKDOWN,
                     reply_to=message.message_id)

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
            self._commands_command_callback(update, context)
            return
