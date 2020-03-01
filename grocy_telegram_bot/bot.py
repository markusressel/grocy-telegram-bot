import logging

from pygrocy import Grocy
from telegram import Update, ParseMode
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, \
    CallbackContext
from telegram_click.argument import Argument, Flag
from telegram_click.decorator import command
from telegram_click.permission import PRIVATE_CHAT
from telegram_click.permission.base import Permission

from grocy_telegram_bot.config import Config
from grocy_telegram_bot.const import *
from grocy_telegram_bot.monitoring.monitor import Monitor
from grocy_telegram_bot.notifier import Notifier
from grocy_telegram_bot.stats import format_metrics, COMMAND_TIME_START, COMMAND_TIME_INVENTORY, COMMAND_TIME_CHORES, \
    COMMAND_TIME_SHOPPING_LIST, COMMAND_TIME_SYSTEM
from grocy_telegram_bot.util import send_message, filter_overdue_chores, product_to_str, chore_to_str, \
    shopping_list_item_to_str

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


class _ConfigAdmins(Permission):

    def __init__(self):
        self._config = Config()

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
        self._grocy = Grocy(
            base_url=f"{config.GROCY_HOST.value}",
            api_key=config.GROCY_API_KEY.value,
            port=config.GROCY_PORT.value)

        self._updater = Updater(token=self._config.TELEGRAM_BOT_TOKEN.value, use_context=True)
        LOGGER.debug("Using bot id '{}' ({})".format(self._updater.bot.id, self._updater.bot.name))

        self._dispatcher = self._updater.dispatcher

        handlers = [
            CommandHandler(COMMAND_START,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._start_callback),
            CommandHandler(COMMAND_CHAT_ID,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._chat_id_callback),
            CommandHandler(COMMAND_INVENTORY,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._inventory_callback),

            CommandHandler(COMMAND_CHORES,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._chores_callback),
            CommandHandler(COMMAND_SHOPPING_LIST,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._shopping_lists_callback),
            CommandHandler(COMMAND_SYSTEM,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._system_info_callback),

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

        self._monitor = None
        chat_ids = self._config.NOTIFICATION_CHAT_IDS.value
        if chat_ids is not None and len(chat_ids) > 0:
            self._notifier = Notifier(self._updater, chat_ids)
            interval = self._config.GROCY_MONITORING_INTERVAL.value
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

    @command(
        name=COMMAND_CHORES,
        description="List overdue chores.",
        arguments=[
            Flag(
                name=["all", "a"],
                description="Show all chores"
            )
        ],
        permissions=CONFIG_ADMINS
    )
    @COMMAND_TIME_CHORES.time()
    def _chores_callback(self, update: Update, context: CallbackContext, all: bool) -> None:
        """
        Show a list of all chores
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id

        chores = self._grocy.chores(True)
        chores = sorted(chores, key=lambda x: x.next_estimated_execution_time)

        overdue_chores = filter_overdue_chores(chores)
        other = [item for item in chores if item not in overdue_chores]

        overdue_item_texts = list(map(chore_to_str, overdue_chores))
        other_item_texts = list(map(chore_to_str, other))

        lines = ["*=> Chores <=*"]
        if all and len(other_item_texts) > 0:
            lines.extend([
                "",
                *other_item_texts
            ])

        if len(overdue_item_texts) > 0:
            lines.extend([
                "",
                "*Overdue:*",
                *overdue_item_texts
            ])

        text = "\n".join(lines).strip()
        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN)

    @command(
        name=COMMAND_INVENTORY,
        description="List product inventory.",
        arguments=[
            Flag(
                name=["missing", "m"],
                description="Show missing products"
            ),
        ],
        permissions=CONFIG_ADMINS
    )
    @COMMAND_TIME_INVENTORY.time()
    def _inventory_callback(self, update: Update, context: CallbackContext, missing: bool) -> None:
        """
        Show a list of all products in the inventory
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id

        # if missing:
        #     # TODO: bugged in pygrocy
        #     products = self._grocy.missing_products(True)
        # else:
        products = self._grocy.stock(True)

        products = sorted(products, key=lambda x: x.name.lower())

        item_texts = list(list(map(product_to_str, products)))
        text = "\n".join([
            "*=> Inventory <=*",
            *item_texts,
        ]).strip()

        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN)

    @command(
        name=COMMAND_SHOPPING_LIST,
        description="List shopping lists.",
        arguments=[
            Argument(
                name=["id"],
                description="Shopping list id",
                type=int,
                example="1",
                optional=True,
                default=1
            ),
            Flag(
                name=["add_missing", "a"],
                description="Add items below minimum stock to the shopping list",
            )
        ],
        permissions=CONFIG_ADMINS
    )
    @COMMAND_TIME_SHOPPING_LIST.time()
    def _shopping_lists_callback(self, update: Update, context: CallbackContext, id: int,
                                 add_missing: bool or None) -> None:
        """
        Show a list of all shopping lists
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id

        if add_missing:
            self._grocy.add_missing_product_to_shopping_list(shopping_list_id=id)

        # TODO: when supported, pass shopping list id here
        shopping_list_items = self._grocy.shopping_list(True)
        shopping_list_items = sorted(shopping_list_items, key=lambda x: x.product.name)

        item_texts = list(list(map(shopping_list_item_to_str, shopping_list_items)))
        text = "\n".join([
            "*=> Shopping List <=*",
            *item_texts,
        ]).strip()

        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN)

    @command(
        name=COMMAND_SYSTEM,
        description="Show grocy system info.",
        permissions=CONFIG_ADMINS
    )
    @COMMAND_TIME_SYSTEM.time()
    def _system_info_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Show grocy system info
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id

        # TODO: pygrocy update
        system_info = self._grocy.shopping_list(True)

        text = "Not yet implemented"
        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN)

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
